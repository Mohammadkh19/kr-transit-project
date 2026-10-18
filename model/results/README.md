# Results

- `shelter.txt`: does a stop have a shelter? 58 labelled stops, split by place (stops < 150 m apart stay together), 5 seeds. No model beats always answering "yes" (accuracy 0.706).
- `next-stop.txt`: which stop comes next? 15% of the links hidden in both directions, 3 seeds. GraphSAGE MRR 0.184 ± 0.075, nearest stop 0.159 ± 0.025. The nearest stop is usually the twin across the road, so it is never right first.