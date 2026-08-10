import numpy as np
import pandas as pd
import os

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- AERMOD: CONC_PLOT.PLT (806 receptores, conc PERIOD em ug/m3)
aermod = pd.read_csv(f'{base}/rodada_aermod/CONC_PLOT.PLT', sep=r'\s+',
                     names=['X', 'Y', 'conc', 'ZELEV', 'ZHILL', 'ZFLAG',
                            'AVE', 'GRP', 'NHRS', 'NETID'],
                     skiprows=8)
aermod['X'] = aermod['X'].round(1)
aermod['Y'] = aermod['Y'].round(1)

# ---- RLINE: media das 120 horas (concentracao horaria em ug/m3)
rline = pd.read_csv(f'{base}/rodada_rline/Output_Road_Numerical.csv',
                    skiprows=12, skipfooter=1, engine='python',
                    header=None, usecols=[0, 1, 2, 3, 4, 5, 6],
                    names=['Year', 'JD', 'Hour', 'X', 'Y', 'Z', 'C'])
rline = rline[rline['C'] > -99.0]
rline_period = rline.groupby(['X', 'Y'])['C'].mean().reset_index()
rline_period['X'] = rline_period['X'].round(1)
rline_period['Y'] = rline_period['Y'].round(1)

# ---- Merge
m = aermod.merge(rline_period, on=['X', 'Y'], suffixes=('_AERMOD', '_RLINE'))
m['ratio'] = m['conc'] / m['C']

print(f'Receptores comparados: {len(m)}')
print(f'AERMOD max: {m["conc"].max():.1f}  |  RLINE max: {m["C"].max():.1f}')
print(f'Media AERMOD: {m["conc"].mean():.1f}  |  Media RLINE: {m["C"].mean():.1f}')
print(f'Ratio AERMOD/RLINE: media {m["ratio"].mean():.3f}  mediana {m["ratio"].median():.3f}')
print(f'R^2 (log): {np.corrcoef(np.log10(m["conc"]), np.log10(m["C"]))[0,1]**2:.4f}')
print()
print('Top 10 receptores por concentracao AERMOD:')
print(m.sort_values('conc', ascending=False).head(10).to_string(index=False))
print()
print('Transecto X=600 (mesma linha do AERMOD plot):')
tr = m[m['X'] == 600.0].sort_values('Y')
print(tr[['Y', 'conc', 'C', 'ratio']].to_string(index=False))
