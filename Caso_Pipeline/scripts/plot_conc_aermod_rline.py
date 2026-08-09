import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as tri

PLT_FILE = 'CONC_PLOT.PLT'
OUT_PNG = '../graficos/conc_periodo_rline.png'

d = pd.read_csv(PLT_FILE, skiprows=8, sep=r'\s+',
                names=['X', 'Y', 'CONC', 'ZELEV', 'ZHILL', 'ZFLAG',
                       'AVE', 'GRP', 'NHRS', 'NET'])

print('Receptores:', len(d))
print('Concentracao media (ug/m3):')
print(d['CONC'].describe())

x = d['X'].values
y = d['Y'].values
c = d['CONC'].values

xi = np.unique(x)
yi = np.unique(y)
X, Y = np.meshgrid(xi, yi)
C = c.reshape(len(yi), len(xi))

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

ax = axes[0]
pc = ax.contourf(X, Y, C, levels=np.linspace(0, np.percentile(c, 99), 40),
                 cmap='inferno')
cb = fig.colorbar(pc, ax=ax)
cb.set_label('Conc. PERIOD (µg/m³)')
ax.axhline(0.0, color='cyan', lw=3, label='Rodovia RLINE (0–1000 m)')
ax.plot([0, 1000], [0, 0], 'c-', lw=3)
ax.set_title('Mapa de concentração PERIOD — RLINE (escala limitada a P99)')
ax.set_xlabel('X (m)'); ax.set_ylabel('Y (m)')
ax.grid(alpha=0.3); ax.legend(loc='upper right')
ax.set_aspect('equal')

ax2 = axes[1]
ax2.plot([0, 1000], [0, 0], 'c-', lw=3, label='Rodovia')
ax2.axvline(600.0, color='k', ls='--', lw=1, label='Transecto X=600 m')
xt = d[d['X'] == 600.0].sort_values('Y')
ax2.plot(xt['Y'], xt['CONC'], 'o-', ms=3, lw=1.5, color='firebrick',
         label='Conc. ao longo de X=600 m')
ax2.set_xlabel('Y (m)'); ax2.set_ylabel('Conc. PERIOD (µg/m³)')
ax2.set_title('Transecto perpendicular à rodovia em X=600 m')
ax2.legend()
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(OUT_PNG, dpi=150)
print('Figura salva em', OUT_PNG)
