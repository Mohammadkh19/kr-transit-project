import datetime
import math
from pathlib import Path

import numpy as np
import sklearn
import torch
import torch_geometric
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from torch_geometric.nn import SAGEConv
from torch_geometric.utils import to_undirected

ROOT = Path(__file__).resolve().parents[1]
SEEDS = range(5)
GROUP_METRES = 150


def metres(a_lat, a_lon, b_lat, b_lon):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b_lon - a_lon) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def place_groups(lat, lon):
    n = len(lat)
    parent = list(range(n))
    def root(i):
        while parent[i] != i:
            i = parent[i]
        return i
    for i in range(n):
        for j in range(i + 1, n):
            if metres(lat[i], lon[i], lat[j], lon[j]) < GROUP_METRES:
                parent[root(i)] = root(j)
    return np.array([root(i) for i in range(n)])


def split_by_place(groups, labelled, seed, test_share=0.3):
    rng = np.random.RandomState(seed)
    names = np.unique(groups[labelled])
    rng.shuffle(names)
    test_groups = names[: int(round(test_share * len(names)))]
    test = labelled & np.isin(groups, test_groups)
    train = labelled & ~np.isin(groups, test_groups)
    return np.flatnonzero(train), np.flatnonzero(test)


class SAGE(torch.nn.Module):
    def __init__(self, n_in, hidden=16):
        super().__init__()
        self.conv1 = SAGEConv(n_in, hidden)
        self.conv2 = SAGEConv(hidden, hidden)
        self.out = torch.nn.Linear(hidden, 1)

    def forward(self, x, edge_index):
        h = self.conv1(x, edge_index).relu()
        h = self.conv2(h, edge_index).relu()
        return self.out(h).squeeze(-1)


def graphsage(x, edge_index, y, train, test, seed):
    torch.manual_seed(seed)
    model = SAGE(x.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)
    target = torch.tensor(y, dtype=torch.float)
    for _ in range(200):
        opt.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(model(x, edge_index)[train], target[train])
        loss.backward()
        opt.step()
    with torch.no_grad():
        return torch.sigmoid(model(x, edge_index)).numpy()[test]


def scores(y_true, p):
    auc = roc_auc_score(y_true, p) if 0 < y_true.sum() < len(y_true) else float("nan")
    return auc, float(((p >= 0.5) == y_true).mean())


b = torch.load(ROOT / "model" / "graph.pt", weights_only=False)
x = b["x"]
x = (x - x.mean(0)) / (x.std(0) + 1e-9)
edge_index = to_undirected(b["edge_index"])
y = b["shelter"].numpy()
labelled = y >= 0
groups = place_groups(b["lat"].numpy(), b["lon"].numpy())

lines = [f"python model/shelter.py   ({datetime.date.today()}; torch {torch.__version__}, "
         f"torch-geometric {torch_geometric.__version__}, scikit-learn {sklearn.__version__})",
         f"{labelled.sum()} labelled stops ({(y == 1).sum()} with a shelter), "
         f"{len(np.unique(groups[labelled]))} place groups (stops < {GROUP_METRES} m apart)",
         "split by place, 30% of the groups in test; ROC-AUC (0.5 = guessing) and accuracy", ""]
results = {"majority": [], "table": [], "GraphSAGE": []}
for seed in SEEDS:
    train, test = split_by_place(groups, labelled, seed)
    yt = y[test]
    majority = float(y[train].mean() >= 0.5)
    table = LogisticRegression(max_iter=1000).fit(x[train].numpy(), y[train])
    runs = {"majority": np.full(len(test), majority),
            "table": table.predict_proba(x[test].numpy())[:, 1],
            "GraphSAGE": graphsage(x, edge_index, y, train, test, seed)}
    lines.append(f"seed {seed}: {len(train)} train, {len(test)} test ({int(yt.sum())} with a shelter)")
    for name, p in runs.items():
        auc, acc = scores(yt, p)
        results[name].append((auc, acc))
        lines.append(f"  {name:<10} ROC-AUC {auc:.3f}  accuracy {acc:.3f}")

lines.append("\nmean and spread over the seeds:")
for name, r in results.items():
    auc, acc = np.array(r).T
    lines.append(f"  {name:<10} ROC-AUC {np.nanmean(auc):.3f} ± {np.nanstd(auc):.3f}   "
                 f"accuracy {acc.mean():.3f} ± {acc.std():.3f}")
text = "\n".join(lines)
print(text)
(ROOT / "model" / "results").mkdir(exist_ok=True)
(ROOT / "model" / "results" / "shelter.txt").write_text(text + "\n", encoding="utf-8")