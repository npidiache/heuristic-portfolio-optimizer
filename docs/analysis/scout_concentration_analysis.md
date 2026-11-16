# Análisis de concentración del reinicio de Dirichlet élite

Generado 2026-07-25 por `scripts/run_scout_concentration_analysis.py` (20 semillas pareadas por configuración; cuatro regímenes y dos universos).

> [!IMPORTANT]
> Diagnóstico exploratorio. Los resultados congelados de la tesis no se modifican. Respalda la sección A.7 del anexo de activación del explorador.

## Concentración de los portafolios finales (universo fijo, sin restricción)

|                                       |   posiciones |   card_efectiva |   peso_maximo |
|:--------------------------------------|-------------:|----------------:|--------------:|
| ('covid_2020', 'ABC original')        |         8.80 |            5.97 |          0.23 |
| ('covid_2020', 'Dirichlet élite')     |         4.40 |            2.10 |          0.68 |
| ('gfc_2007_2009', 'ABC original')     |         6.90 |            5.42 |          0.23 |
| ('gfc_2007_2009', 'Dirichlet élite')  |         3.10 |            2.17 |          0.60 |
| ('war_2022', 'ABC original')          |         9.45 |            7.41 |          0.17 |
| ('war_2022', 'Dirichlet élite')       |         5.05 |            2.63 |          0.55 |
| ('2023_stability', 'ABC original')    |         9.00 |            6.55 |          0.21 |
| ('2023_stability', 'Dirichlet élite') |         4.90 |            2.12 |          0.65 |

## Efecto de las restricciones de concentración

| escenario                |   dirichlet |   abc |   diferencia |   card_efectiva |   peso_maximo | celdas_favorables_holm   |
|:-------------------------|------------:|------:|-------------:|----------------:|--------------:|:-------------------------|
| Sin restricción          |       2.870 | 2.145 |        0.726 |           2.434 |         0.588 | 8 de 8                   |
| Piso de cinco posiciones |       2.832 | 2.145 |        0.687 |           2.608 |         0.557 | 8 de 8                   |
| Tope duro de 20%         |       2.387 | 2.102 |        0.285 |           5.616 |         0.201 | 7 de 8                   |

El tope duro de peso máximo es la única restricción que controla efectivamente la concentración: el piso de cinco posiciones se satisface manteniendo un peso máximo superior al 50 %. Bajo el tope, la ventaja del operador se reduce pero conserva significancia estadística tras la corrección de Holm, de modo que una parte de la diferencia inicial era atribuible a la concentración y otra corresponde a una mejora de búsqueda.
