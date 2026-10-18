import datetime
from pathlib import Path

import numpy as np
import torch
import torch_geometric
from torch_geometric.nn import SAGEConv
from torch_geometric.utils import negative_sampling, to_undirected

ROOT = Path(__file__).resolve().parents[1]
SEEDS = range(3)
HIDE = 0.15


class Encoder(torch.nn.Module):
    def __init__(self, n_in, hidden=32):
        super().__init__()
        self.conv1 = SAGEConv(n_in, hidden)
        self.conv2 = SAGEConv(hidden, hidden)

    def forward(self, x, edge_index):
        return self.conv2(self.conv1(x, edge_index).relu(), edge_index)


def ranks(score, hidden, known, n):
    out = []
    for a, b in hidden:
        s = score(a).copy()
        s[a] = -np.inf
        for k in known.get(a, ()):
            if k != b:
                s[k] = -np.inf
        out.append(int((s > s[b]).sum()) + 1)
    return np.array(out)


def summary(r):
    return f"MRR {np.mean(1 / r):.3f}  Hits@1 {np.mean(r == 1):.3f}  Hits@5 {np.mean(r <= 5):.3f}"


b = torch.load(ROOT / "model" / "graph.pt", weights_only=False)
lat, lon = b["lat"].numpy(), b["lon"].numpy()
n = len(lat)
pos = np.column_stack([(lat - lat.mean()) / lat.std(), (lon - lon.mean()) / lon.std()])
x = torch.tensor(np.hstack([pos, b["x"].numpy()]), dtype=torch.float)
edges = [tuple(e) for e in b["edge_index"].T.tolist()]
pairs = sorted({tuple(sorted(e)) for e in edges})
dist = np.sqrt(((pos[:, None, :] - pos[None, :, :]) ** 2).sum(-1))

lines = [f"python model/next_stop.py   ({datetime.date.today()}; torch {torch.__version__}, "
         f"torch-geometric {torch_geometric.__version__})",
         f"{n} stops, {len(edges)} next-stop links ({len(pairs)} stop pairs); "
         f"{HIDE:.0%} of the pairs hidden per seed", ""]
all_r = {"distance": [], "GraphSAGE": []}
for seed in SEEDS:
    rng = np.random.RandomState(seed)
    hidden_pairs = {pairs[i] for i in rng.permutation(len(pairs))[: int(HIDE * len(pairs))]}
    train = [e for e in edges if tuple(sorted(e)) not in hidden_pairs]
    hidden = [e for e in edges if tuple(sorted(e)) in hidden_pairs]
    known = {}
    for a, c in train:
        known.setdefault(a, set()).add(c)
    train_index = torch.tensor(train, dtype=torch.long).T

    r_dist = ranks(lambda a: -dist[a], hidden, known, n)

    torch.manual_seed(seed)
    enc = Encoder(x.shape[1])
    opt = torch.optim.Adam(enc.parameters(), lr=0.01)
    message_index = to_undirected(train_index)
    for _ in range(300):
        opt.zero_grad()
        z = enc(x, message_index)
        neg = negative_sampling(train_index, num_nodes=n, num_neg_samples=train_index.shape[1])
        pos_s = (z[train_index[0]] * z[train_index[1]]).sum(-1)
        neg_s = (z[neg[0]] * z[neg[1]]).sum(-1)
        loss = torch.nn.functional.binary_cross_entropy_with_logits(
            torch.cat([pos_s, neg_s]), torch.cat([torch.ones_like(pos_s), torch.zeros_like(neg_s)]))
        loss.backward()
        opt.step()
    with torch.no_grad():
        z = enc(x, message_index).numpy()
    r_gnn = ranks(lambda a: z @ z[a], hidden, known, n)

    all_r["distance"].append(r_dist)
    all_r["GraphSAGE"].append(r_gnn)
    lines.append(f"seed {seed}: {len(train)} training links, {len(hidden)} hidden links")
    lines.append(f"  distance   {summary(r_dist)}")
    lines.append(f"  GraphSAGE  {summary(r_gnn)}")

lines.append("\nmean and spread over the seeds:")
for name, rs in all_r.items():
    mrr = np.array([np.mean(1 / r) for r in rs])
    h1 = np.array([np.mean(r == 1) for r in rs])
    lines.append(f"  {name:<10} MRR {mrr.mean():.3f} ± {mrr.std():.3f}   Hits@1 {h1.mean():.3f} ± {h1.std():.3f}")
text = "\n".join(lines)
print(text)
(ROOT / "model" / "results").mkdir(exist_ok=True)
(ROOT / "model" / "results" / "next-stop.txt").write_text(text + "\n", encoding="utf-8")