import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

aermod = pd.read_csv(f'{base}/rodada_aermod/CONC_PLOT.PLT', sep=r'\s+',
                     names=['X', 'Y', 'conc', 'ZELEV', 'ZHILL', 'ZFLAG',
                            'AVE', 'GRP', 'NHRS', 'NETID'], skiprows=8)
aermod['X'] = aermod['X'].round(1)
aermod['Y'] = aermod['Y'].round(1)

rline = pd.read_csv(f'{base}/rodada_rline/Output_Road_Numerical.csv',
                    skiprows=12, skipfooter=1, engine='python',
                    header=None, usecols=[0, 1, 2, 3, 4, 5, 6],
                    names=['Year', 'JD', 'Hour', 'X', 'Y', 'Z', 'C'])
rline = rline[rline['C'] > -99.0]
rline_period = rline.groupby(['X', 'Y'])['C'].mean().reset_index()
rline_period['X'] = rline_period['X'].round(1)
rline_period['Y'] = rline_period['Y'].round(1)

m = aermod.merge(rline_period, on=['X', 'Y'], suffixes=('_AERMOD', '_RLINE'))
m['ratio'] = m['conc'] / m['C']
m.sort_values('Y', inplace=True)

fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))

# 1) Transecto X=600
tr = m[m['X'] == 600.0].sort_values('Y')
axes[0].plot(tr['Y'], tr['conc'], '-o', ms=3, label='AERMOD RLINE (PERIOD)')
axes[0].plot(tr['Y'], tr['C'], '-s', ms=3, label='RLINE standalone (media 120 h)')
axes[0].set_xlabel('Distancia transversal Y (m)  [X = 600 m]')
axes[0].set_ylabel('Concentracao (ug/m3)')
axes[0].set_title('Transecto em X=600 m')
axes[0].legend()
axes[0].grid(alpha=0.3)

# 2) Scatter 1:1
ax = axes[1]
ax.loglog(m['C'], m['conc'], '.', ms=4, alpha=0.6)
lims = (m[['C', 'conc']].min().min(), m[['C', 'conc']].max().max())
ax.plot([lims[0], lims[1]], [lims[0], lims[1]], 'k--', lw=0.8, label='1:1')
ax.loglog([lims[0], lims[1]], [lims[0] * 0.64, lims[1] * 0.64], 'r:', lw=0.8,
          label='fator 0.64')
ax.set_xlabel('RLINE standalone (ug/m3)')
ax.set_ylabel('AERMOD RLINE (ug/m3)')
ax.set_title('Scatter log-log (806 receptores)\nR2(log)=0.96')
ax.legend()
ax.grid(alpha=0.3, which='both')

# 3) Ratio ao longo do transecto
axes[2].plot(tr['Y'], tr['ratio'], '-o', ms=4, label='X=600')
axes[2].axhline(1.0, color='k', ls='--', lw=0.8)
axes[2].axhline(0.64, color='r', ls=':', lw=0.8)
axes[2].set_xlabel('Distancia transversal Y (m)')
axes[2].set_ylabel('Razao AERMOD / RLINE')
axes[2].set_title('Razao de concentracoes')
axes[2].legend()
axes[2].grid(alpha=0.3)

fig.suptitle('Comparacao: AERMOD (RLINE implementado) vs RLINE v1.2 standalone\n'
             'Rodovia 0-1000 m em Y=0, QEMIS=0.02 g/m/s, periodo 120 h (mar/1988)', fontsize=11)
fig.tight_layout()
fig.savefig(f'{base}/graficos/conc_aermod_vs_rline.png', dpi=150)
print('Figura salva em graficos/conc_aermod_vs_rline.png')
