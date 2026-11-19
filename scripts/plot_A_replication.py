"""Plot both A seeds and keep the parser diagnostic visually separate."""

import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator
import numpy as np
from twenty_bits.worlds import ROOT


def main():
    summaries={seed:json.loads((ROOT/f"results/main_A{seed}/summary.json").read_text()) for seed in (11,23)}
    replication=json.loads((ROOT/"results/main_A23/replication_summary.json").read_text())
    folder=ROOT/"results/main_A23/charts"
    folder.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,
        "axes.spines.top":False,"axes.spines.right":False,"svg.fonttype":"none"})
    colors={11:"#276a92",23:"#b56837"}
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    for ax,key,title in ((axes[0,0],"eig_per_question","Fixed development · expected bits/question"),
                         (axes[0,1],"win_rate","Fixed development · win rate")):
        for seed,summary in summaries.items():
            dev=summary["development"];x=[int(k) for k in dev]
            y=[dev[str(k)]["point"][key] for k in x]
            ci=[dev[str(k)]["ci95"][key+"_ci95"] for k in x]
            ax.plot(x,y,marker="o",ms=4,color=colors[seed],label=f"A seed {seed}")
            ax.fill_between(x,[v[0] for v in ci],[v[1] for v in ci],color=colors[seed],alpha=.08)
        ax.set(title=title,xlabel="Optimizer update",ylim=(-.02,1.04),xticks=[0,4,8,12,16,20,24,28,30])
        ax.grid(axis="y",alpha=.2)
        ax.legend(frameon=False)
        if key=="eig_per_question":ax.axhline(1,color="#2a826b",ls="--",lw=1)
    for ax,domain,sizes in ((axes[1,0],"animals",[32,128]),(axes[1,1],"synthetic",[32,128,256])):
        cells={seed:[next(r for r in summary["frozen_evaluation"]["cells"] if (r["domain"],r["n"],r["noise"])==(domain,n,0)) for n in sizes] for seed,summary in summaries.items()}
        x=np.arange(len(sizes))
        groups=[("Raw base",[r["base"] for r in cells[11]],"#8b9ba5",-.2),
                ("A11 primary",[r["endpoint"] for r in cells[11]],colors[11],0),
                ("A23 primary",[r["endpoint"] for r in cells[23]],colors[23],.2)]
        for label,rows,color,shift in groups:
            y=np.array([r["eig_per_question"] for r in rows]);ci=[r["eig_per_question_ci95"] for r in rows]
            ax.errorbar(x+shift,y,yerr=np.maximum(0,[y-np.array([v[0] for v in ci]),np.array([v[1] for v in ci])-y]),fmt="o",capsize=3,color=color,label=label)
        ax.axhline(1,color="#2a826b",ls="--",lw=1,label="Noiseless ceiling")
        ax.set(title=f"Frozen {domain} · noiseless EIG/question",xticks=x,xticklabels=[f"N={n}" for n in sizes],ylim=(-.02,1.04))
        ax.grid(axis="y",alpha=.2)
        ax.legend(frameon=False,fontsize=8,loc="lower right")
    fig.suptitle("Twenty Bits · replication across A seeds 11 and 23",fontsize=16,fontweight="bold")
    fig.supxlabel("Development uses 8 fixed small cases; frozen cells use 28 paired cases. Shading/error bars resample games within a seed.",fontsize=9)
    fig.savefig(folder/"A-replication.png",dpi=180);fig.savefig(folder/"A-replication.svg");plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,3.7),constrained_layout=True)
    for ax,key,title in zip(axes,("eig_per_question","win_rate","invalid_rate"),("Expected bits/question","Win rate","Invalid questions/question")):
        for noise,marker in ((0,"o"),(.1,"s")):
            rows=[r for r in replication["suffix_diagnostic_only"] if r["noise"]==noise]
            x=np.array([r["n"] for r in rows])
            for label,field,color,style in (("Primary","primary_A23",colors[23],"-"),("Suffix diagnostic","diagnostic_A23","#2a826b","--")):
                ax.plot(x,[r[field][key] for r in rows],marker=marker,color=color,ls=style,label=f"{label}, p={noise:g}")
        ax.set(title=title,xscale="log",xticks=[32,128,256],xticklabels=["32","128","256"],xlabel="Synthetic N",ylim=(-.02,1.04))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.grid(axis="y",alpha=.2)
    axes[0].axhline(1,color="#999999",ls=":",lw=1)
    axes[0].axhline(.5310044064,color="#999999",ls=":",lw=1)
    axes[1].legend(frameon=False,fontsize=8)
    fig.suptitle("A23 suffix tolerance · auxiliary parser diagnostic only",fontsize=15,fontweight="bold")
    fig.supxlabel("Fresh paired-seed rollouts; the tolerant parser is excluded from every primary result and all training.",fontsize=9)
    fig.savefig(folder/"suffix-diagnostic.png",dpi=180);fig.savefig(folder/"suffix-diagnostic.svg");plt.close(fig)

    for path in folder.glob("*.svg"):
        path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines())+"\n")


if __name__=="__main__":main()
