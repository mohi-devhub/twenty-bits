"""Offline B41 forecast using both A seeds; this does not authorize a run."""

from collections import defaultdict
from decimal import Decimal
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import numpy as np
from twenty_bits.budget import Ledger
from twenty_bits.tinker_transport import rates,save_json
from twenty_bits.worlds import ROOT


def main():
    summaries={seed:json.loads((ROOT/f"results/main_A{seed}/summary.json").read_text()) for seed in (11,23)}
    games={seed:[json.loads(line) for line in gzip.open(ROOT/f"results/main_A{seed}/games.jsonl.gz","rt")] for seed in (11,23)}
    original=json.loads((ROOT/"research/main_options_after_pilot.json").read_text())
    config=json.loads((ROOT/"experiments/main_A23.json").read_text())
    rate={k:float(v)/1e6 for k,v in rates(config["primary_model"]).items()}
    def sample(gs,cache=0):
        return sum(g["prompt_tokens"]*((1-cache)*rate["prefill"]+cache*rate["cached_prefill"])+g["output_tokens"]*rate["sample"] for g in gs)
    values=defaultdict(list)
    for seed,s in summaries.items():
        for row in s["updates"]:
            group=[g for g in games[seed] if g["kind"]=="train" and g["update"]==row["update"]]
            values[row["n"]].append((sample(group)+float(row["gradient_usd"]))/8)
    profiles={}
    for n,observed in values.items():
        ref=original["training_profiles"][f"{n}/p0"]
        noisy=original["training_profiles"][f"{n}/p0.1"]
        floor=ref["sampling_usd"]+ref["gradient_usd"]
        value=max(floor,float(np.mean(observed)),float(np.quantile(observed,.75)))
        multiplier=max(1,(noisy["sampling_usd"]+noisy["gradient_usd"])/floor)
        profiles[str(n)]={"uncached_A_sampling_plus_gradient_per_game_usd":value,
            "B_reference_multiplier":multiplier,"observed_A_group_per_game_costs":observed,
            "reference_floor_usd":floor}
    training=sum(row["games_per_seed"]*profiles[str(row["n"])]["uncached_A_sampling_plus_gradient_per_game_usd"]*profiles[str(row["n"])]["B_reference_multiplier"] for row in config["curriculum"])
    raw=[g for g in games[11] if g["kind"]=="eval_base"]
    endpoints=[raw]+[[g for g in games[seed] if g["kind"]=="eval_endpoint"] for seed in (11,23)]
    cache=min(.6,*[sum(g["prompt_cache_hit_tokens"] for g in cohort)/sum(g["prompt_tokens"] for g in cohort) for cohort in endpoints])
    endpoint=uncached_endpoint=0
    for cell in summaries[23]["frozen_evaluation"]["cells"]:
        groups=[[g for g in cohort if (g["domain"],g["n"],g["noise"])==(cell["domain"],cell["n"],cell["noise"])] for cohort in endpoints]
        endpoint+=max(sample(gs,cache) for gs in groups)
        uncached_endpoint+=max(sample(gs) for gs in groups)
    dev=max(sample([g for g in games[seed] if g["kind"]=="dev" and g["update"]==step]) for seed in (11,23) for step in config["development_checks"])*len(config["development_checks"])
    storage=sum(float(row["estimated_usd"]) for row in config["permanent_storage"].values())
    total=training+endpoint+dev+storage
    status=Ledger(ROOT/"ledger.json").status()
    result={"authorized_to_start_now":False,"requires_user_confirmation_at_A23_gate":True,
        "condition":"B","seed":41,"noise":.1,"updates":30,"group_size":8,
        "training_games":240,"new_development_games":64,"frozen_endpoint_games":280,
        "new_raw_control_games":0,"hard_mode_already_completed_on_A23":True,
        "training_usd":training,"development_usd":dev,"endpoint_usd":endpoint,
        "native_no_expiry_checkpoint_storage_estimate_usd":storage,"storage_reserve_coverage_days":30,
        "total_before_margin_usd":total,"total_with_1_5_margin_usd":total*1.5,
        "zero_cache_reference_before_extra_margin_usd":training+dev+uncached_endpoint+storage,
        "available_usd":status["available_usd"],"fits_with_margin":Decimal(str(total*1.5))<=Decimal(status["available_usd"]),
        "training_profiles":profiles,"endpoint_cache_credit":cache,
        "method":"Two observed A seeds; uncached sampling plus gradient cost by N, using max(original floor, pooled mean, pooled upper quartile), multiplied by the original noisy/noiseless free-reference cost ratio. Endpoint uses the most expensive strict primary cohort per cell and at most 60% cache credit. No extra hard mode, raw endpoint, suffix diagnostic or external reupload is forecast.",
        "limits":"B training behavior is still unobserved; its noisy-reference multiplier may miss new behavior. Per-call ledger holds still bound dispatch. No protocol changes or B41 authorization follow from this forecast."}
    save_json(ROOT/"research/B41_forecast_after_A23.json",result)
    print(json.dumps({k:v for k,v in result.items() if k!="training_profiles"},indent=2))


if __name__=="__main__":main()
