"""Evaluate behavioural bot signals on the public "Web robot detection - Server logs" sessions (March 2018, 67,352 sessions,
label ROBOT "as labelled by the dataset"). Defender's view only: what separates robots from humans, and how stable it is.

  1. AUC of each feature on its own (0.5 = useless, 1.0 = perfect; direction ignored);
  2. two models with 5-fold stratified cross-validation (no timestamps in the files, so no time split - said in the limits):
     logistic regression on log-scaled features, and gradient boosting (scikit-learn);
  3. a "lab" model that uses only the features the local robot lab can compute, then scores the lab sessions (lab/).
Outputs: data/output/webrobots_feature_auc.csv, webrobots_models.csv, lab_scores.csv (if the lab ran).
Run:  python src/signals_eval.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from common import OUT, PUBLIC

LAB_FEATURES = ["NUMBER_OF_REQUESTS", "TOTAL_DURATION", "AVERAGE_TIME", "STANDARD_DEVIATION", "REPEATED_REQUESTS",
                "HTTP_RESPONSE_4XX", "IMAGES", "TOTAL_HTML", "NIGHT", "HEAD_METHOD", "POST_METHOD"]


def models() -> dict:
    log_scale = FunctionTransformer(lambda x: np.log1p(np.clip(x, 0, None)))   # counts and durations are very skewed
    return {"logistic regression": make_pipeline(log_scale, StandardScaler(), LogisticRegression(max_iter=2000)),
            "gradient boosting": HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, random_state=42)}


def cross_validate(X: pd.DataFrame, y: pd.Series, name: str, model) -> dict:
    """5 folds; report mean AUC, its spread across folds (stability) and recall at a 1 % false-positive rate."""
    aucs, recalls = [], []
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=42).split(X, y):
        p = model.fit(X.iloc[tr], y.iloc[tr]).predict_proba(X.iloc[te])[:, 1]
        aucs.append(roc_auc_score(y.iloc[te], p))
        fpr, tpr, _ = roc_curve(y.iloc[te], p)
        recalls.append(np.interp(0.01, fpr, tpr))
    return {"model": name, "auc_mean": round(np.mean(aucs), 4), "auc_fold_sd": round(np.std(aucs), 4),
            "recall_at_1pct_fpr": round(np.mean(recalls), 3)}


def main() -> None:
    df = pd.read_parquet(PUBLIC / "webrobots_sessions.parquet")
    y = df["ROBOT"].astype(int)
    X = df.drop(columns=["ID", "ROBOT"])
    # a few semantic features are empty for some sessions (logged in docs/data_issues_log.md): 0 = "no page content seen"
    X = X.fillna(0)
    # 1) each feature alone
    rows = []
    for c in X.columns:
        auc = roc_auc_score(y, X[c])
        rows.append({"feature": c, "auc": round(max(auc, 1 - auc), 4), "higher_for": "robots" if auc >= .5 else "humans",
                     "median_humans": X.loc[y == 0, c].median(), "median_robots": X.loc[y == 1, c].median()})
    fa = pd.DataFrame(rows).sort_values("auc", ascending=False)
    fa.to_csv(OUT / "webrobots_feature_auc.csv", index=False)
    # 2) models on all features, then on the lab subset
    res = [{**cross_validate(X, y, n, m), "features": f"all {X.shape[1]}"} for n, m in models().items()]
    res += [{**cross_validate(X[LAB_FEATURES], y, n, m), "features": f"lab subset {len(LAB_FEATURES)}"}
            for n, m in models().items()]
    pd.DataFrame(res).to_csv(OUT / "webrobots_models.csv", index=False)
    print(fa.head(5)[["feature", "auc", "higher_for"]].to_string(index=False))
    print(pd.DataFrame(res).to_string(index=False))
    # 3) score the local lab sessions with a model trained on the public data (lab subset only)
    lab = OUT / "lab_sessions.csv"
    if lab.exists():
        s = pd.read_csv(lab)
        m = models()["gradient boosting"].fit(X[LAB_FEATURES], y)
        s["robot_score"] = m.predict_proba(s[LAB_FEATURES])[:, 1].round(3)
        s[["visitor", "kind"] + LAB_FEATURES + ["robot_score"]].to_csv(OUT / "lab_scores.csv", index=False)
        print(s[["visitor", "kind", "NUMBER_OF_REQUESTS", "robot_score"]].to_string(index=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
