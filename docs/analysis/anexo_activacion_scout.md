# Anexo. Activación del mecanismo scout: diagnóstico, matices y una línea de extensión

> Anexo complementario al comentario 9 del jurado (valor y sensibilidad del parámetro
> PFA). Las cifras de activación y desempeño provienen del diagnóstico de activación
> reproducible sobre los datos congelados del estudio (`scripts/run_scout_activation_
> telemetry.py` y sus extensiones).
> **Los resultados centrales de la tesis no se modifican:** las tablas canónicas, los
> parámetros calibrados y las conclusiones del cuerpo principal permanecen intactos y
> verificados por las pruebas de regresión del repositorio. Lo que aquí se presenta es un
> diagnóstico posterior y una línea de trabajo futuro.

## A.1. Motivación: una línea de mejora incremental sobre el ABC

El punto de partida de esta investigación es sólido y no está en discusión: el algoritmo
ABC original supera consistentemente a los benchmarks clásicos —la optimización
media-varianza (PMVG) y la asignación equiponderada (1/N)— en el ratio de Sortino, en
todos los regímenes de volatilidad. Esa es la hipótesis central de la tesis y se mantiene.

Sobre esa base, el trabajo persigue una mejora incremental. El ABC tiene limitaciones
conocidas en su capacidad de explotación local; para atacarlas se evaluó primero el
ABC-FA de Tuba y Bacanin (2014), que inserta un movimiento tipo luciérnaga en la fase de
abejas empleadas. En los escenarios de este estudio, sin embargo, esa variante no ofrece
un buen desempeño (su mecanismo sí se ejecuta, y aun así queda por debajo del ABC
original). Ante ese resultado, la tesis propone alterar específicamente la **fase de
scout** del ABC —mediante un disparador probabilístico (PFA), una atracción guiada por
élites (ABC-FAEM) y una atracción gravitacional (ABC-GSA)— con el objetivo de superar las
limitaciones del original. En ningún momento se plantean estas variantes como una
panacea, sino como intentos de mejora sujetos a verificación empírica.

El diagnóstico que motiva este anexo surge al responder con rigor el comentario 9 del
jurado: **por la dimensionalidad del problema, esos mecanismos de scout casi no se
alcanzan y permanecen dormidos bajo la configuración calibrada.** Esto abre dos preguntas
legítimas que este anexo responde con honestidad: (i) ¿cómo se logra que el scout se
active? y (ii) si se activa, ¿qué tan buenos son los resultados?

## A.2. El scout no se activa bajo la calibración

El umbral de abandono se deriva de forma proporcional a la dimensión, `max_trials = 0.6 ×
25 abejas × 20 activos = 300`. Pero el contador de intentos de una abeja solo crece cuando
un movimiento no mejora su fuente, y dentro del presupuesto de 60 iteraciones dicho
contador alcanza un máximo observado cercano a **19**. Ninguna abeja supera el umbral de
300 y la fase de scout **no se ejecuta en ninguna corrida** (ambos universos, los cuatro
regímenes, las 20 semillas). Dado que las variantes solo redefinen el movimiento del
scout, con este dormido las diferencias entre el ABC original, el ABC-FAEM y el ABC-GSA
en las tablas de resultados provienen de sus trayectorias estocásticas, no del mecanismo
de scout en sí.

## A.3. Instrumentación: telemetría de activación

Para pasar de la inferencia indirecta a la medición directa, se instrumentó cada ejecución
con el número de activaciones del scout y las iteraciones en que ocurren. El Cuadro A.1
reporta las activaciones medias por corrida (ambos universos) para la configuración
calibrada y para umbrales de activación proporcionales al presupuesto de iteraciones.

**Cuadro A.1. Activaciones medias del scout por corrida.**

| Configuración | COVID-19 | GFC | Guerra | Estabilidad |
| --- | ---: | ---: | ---: | ---: |
| ABC original (calibrado) | 0.0 | 0.0 | 0.0 | 0.0 |
| ABC-GSA congelado (`max_trials`=300) | 0.0 | 0.0 | 0.0 | 0.0 |
| ABC-GSA activo (`max_trials`=9) | 10.9 | 9.9 | 9.8 | 10.4 |
| ABC-FAEM activo (`max_trials`=9) | 12.4 | 11.7 | 11.3 | 11.9 |
| Reinicio Dirichlet (fracción 0.15) | 12.3 | 13.1 | 10.9 | 12.3 |

Bajo la calibración, el mecanismo permanece dormido; un umbral proporcional al horizonte
lo vuelve operativo a una tasa controlada (~10-13 activaciones por corrida, cerca del
0,4% de las ~3.100 evaluaciones de la función objetivo).

## A.4. Al activar los mecanismos: matices

Responder «¿qué tan buenos son si se activan?» exige medirlos con semillas pareadas
idénticas entre configuraciones (para que las pruebas sean genuinamente pareadas). El
Cuadro A.2 muestra el Sortino medio por semilla agregado sobre las ocho celdas
régimen-universo.

**Cuadro A.2. Sortino medio por semilla (agregado, 8 celdas).**

| Configuración | Sortino medio |
| --- | ---: |
| Reinicio Dirichlet f=0.15 *(extensión, §A.6)* | **2.870** |
| ABC original | 2.145 |
| ABC-GSA congelado (dormido) | 1.975 |
| ABC-FAEM activo mt=9 | 1.964 |
| ABC-GSA activo mt=9 | 1.860 |
| PMVG (media-varianza) | 1.161 |
| 1/N (equiponderado) | 0.920 |

El resultado es matizado, y esa honestidad es parte del aporte:

- **A veces la mejora es marginal.** Al activar la atracción por luciérnagas (ABC-FAEM
  mt=9) el desempeño apenas se distingue del ABC original —marginal e inconsistente entre
  regímenes—, como ya anticipaba el diagnóstico proporcional previo
  ([`faem_activation_calibration.md`](faem_activation_calibration.md)).
- **A veces incluso empeora.** Al activar la atracción gravitacional (ABC-GSA mt=9), el
  desempeño cae por debajo del ABC original: pierde en las 8 celdas frente a él y de forma
  Holm-significativa en 6 de 8, incluidas las de baja volatilidad (estabilidad). Este
  comportamiento es estructural —no depende del régimen ni del universo— y se explica en
  §A.5.
- **Pero en ningún caso se pierde la hipótesis central.** El «empeora» es siempre
  *respecto del ABC original*, nunca respecto de los benchmarks clásicos: incluso el peor
  caso (ABC-GSA activo, 1.860) permanece muy por encima de PMVG (1.161) y de 1/N (0.920).
  Es decir, activar los mecanismos redistribuye el desempeño *dentro* de la familia
  bioinspirada, sin devolver la ventaja a los métodos clásicos.

**Cuadro A.3. ABC-GSA activo vs. ABC original, por celda (Δ = GSA activo − ABC original).**

| Régimen | Δ universo *fixed* | Δ universo *dynamic* |
| --- | ---: | ---: |
| COVID-19 (crisis) | −0.537 (Holm-sig.) | −0.462 (Holm-sig.) |
| GFC 2008 (crisis) | −0.055 (sig.) | −0.042 (no sig.) |
| Guerra 2022 (vol. alta) | −0.341 (Holm-sig.) | −0.254 (Holm-sig.) |
| Estabilidad 2023-24 (baja vol.) | −0.236 (Holm-sig.) | −0.352 (Holm-sig.) |

## A.5. El problema de fondo: el sesgo de normalización y la geometría

Los dos hallazgos de §A.4 —activar no basta, y el movimiento en caja puede incluso
estorbar— apuntan a una causa común de naturaleza geométrica. Conviene precisarla.

El conjunto de portafolios *long-only* factibles —vectores de pesos no negativos que suman
uno— constituye el **símplex de probabilidad**: un objeto cuyos vértices representan la
concentración total en un único activo, cuyo baricentro corresponde a la asignación
equiponderada (1/N) y cuyas aristas y caras corresponden a portafolios que emplean solo un
subconjunto de los activos (Figura A.1). Los movimientos de recuperación que operan en el
**espacio de caja** —el reinicio aleatorio uniforme, el desplazamiento tipo luciérnaga, o
la atracción gravitacional del ABC-GSA— generan candidatos que en general no pertenecen a
este conjunto y exigen una **renormalización posterior** (dividir por la suma de pesos).
Ese parche introduce un sesgo: distorsiona la perturbación pretendida y, además, el ABC-GSA
apunta al centro de masa del enjambre —un consenso que suele ser mediocre— en lugar de a
la región de las mejores soluciones. La combinación de ambos efectos explica por qué su
activación resta en vez de sumar.

La pregunta natural es entonces: ¿cómo superar el sesgo de normalización? La respuesta que
propone la extensión es recomponer la solución **directamente sobre el símplex**, sin pasar
por el espacio de caja.

## A.6. Línea de extensión: reinicio Dirichlet nativo al símplex

> Esta sección corresponde a la **extensión de la tesis**, no a sus resultados congelados.

Se propone un operador de reinicio que, cuando una abeja se estanca, la recompone mediante
una extracción de una **distribución de Dirichlet concentrada alrededor de la dirección
media de las soluciones élite**. La distribución de Dirichlet reside sobre el símplex por
construcción, de modo que todo candidato es un portafolio factible **sin necesidad de
reparación ni renormalización**; su vector de concentración regula el equilibrio entre
intensificación (permanecer cerca de la élite) y exploración (diversificar la composición).
Mientras que el reinicio en caja genera puntos que luego deben forzarse a ser válidos, el
muestreo de Dirichlet genera portafolios válidos desde el origen y los orienta hacia la
región donde la colonia ha identificado las mejores soluciones.

![Figura A.1. Reubicación de una abeja estancada sobre el símplex de portafolios según la política de recuperación.](../figures/fig_simplex_scout.png)

**Figura A.1.** Reubicación de una abeja estancada sobre el símplex de portafolios de tres
activos, según la política de recuperación. El reinicio uniforme (izquierda) dispersa los
candidatos por todo el símplex, ignorando la información de la colonia; el movimiento tipo
luciérnaga (centro) apenas desplaza la abeja de su posición estancada; el reinicio
Dirichlet propuesto (derecha) concentra los candidatos alrededor de la dirección media de
las soluciones élite, generando portafolios factibles por construcción.

En la evaluación con semillas pareadas, el reinicio Dirichlet (fracción 0.15) eleva el
Sortino medio por semilla de 2.145 (ABC original) a **2.870**, y obtiene además el mejor
valor medio de la función objetivo ejecutada, lo que indica que encuentra mejores óptimos
del problema y no simplemente valores más favorables de la métrica de evaluación. Las
pruebas de Wilcoxon frente al ABC original, corregidas con el procedimiento de Holm (1979)
dentro de cada celda, resultan significativas y a su favor en **las ocho celdas**
régimen-universo; ninguna otra configuración examinada gana una sola celda corregida.

Como control adicional frente a la selección, el ratio de Sharpe deflactado (Bailey y
López de Prado, 2014) del mejor portafolio del operador supera 0,95 en cuatro de las ocho
celdas —COVID-19 y estabilidad, en ambos universos, con valores de hasta 1,000— pero se
sitúa entre 0,51 y 0,72 en la GFC y la guerra. La lectura honesta: la superioridad
*relativa* del operador frente al ABC original sobrevive al control por comparaciones
múltiples en todas las celdas, mientras que su capacidad *absoluta* de generar desempeño
distinguible del azar queda establecida solo en los regímenes de menor turbulencia.

## A.7. Una metodología, no un mecanismo

El aporte de esta línea no es un movimiento de recuperación en particular, sino un
**procedimiento** aplicable a cualquier mecanismo del scout: instrumentar la activación
como diagnóstico de primera clase, forzar la activación con un umbral proporcional, medir
su efecto con estadística pareada honesta y —al constatar que la geometría del espacio de
soluciones es la que determina el valor de la recuperación— rediseñar el movimiento para
que respete esa geometría. El reinicio Dirichlet es la instanciación de ese procedimiento
para el problema *long-only*; el mismo camino se habría seguido con cualquier otro
mecanismo candidato. Ese es el sentido en que la extensión generaliza el trabajo de la
tesis en lugar de reemplazarlo.

## A.8. Relación con la literatura

El fenómeno de un operador de scout inactivo bajo la calibración empleada no es exclusivo
de este trabajo. Bullinaria y AlYahya (2014) observaron empíricamente que, con la
calibración por defecto del ABC, la fase de scout esencialmente no se activa, y la
declararon redundante mediante ablación sobre el umbral de abandono. Singh y Deep (2019)
llegaron a una conclusión afín sobre el balance exploración-explotación del ABC, señalando
que el scout puede volverse redundante en alta dimensión. Hussain et al. (2020), mediante
un análisis componente a componente basado en diversidad, reportan igualmente que el
componente de scout puede resultar poco contributivo. La contribución de este anexo
respecto a esa línea es doble: instrumentar la activación ligada a una función objetivo
financiera y —a diferencia de esos trabajos, que se detienen en el diagnóstico— acoplar la
auditoría a un rediseño que recupera valor.

El uso de la distribución de Dirichlet para representar pesos de portafolios *long-only*
sobre el símplex está establecido en la literatura financiera (André y Coqueret, 2020;
Yang, Park y Lee, 2022; Le Courtois y Xu, 2024), aunque en contextos de aprendizaje por
refuerzo o de construcción directa del conjunto eficiente, y no como operador dentro de una
metaheurística. La combinación específica —disparador por estancamiento, muestreo nativo
al símplex y condicionamiento a la media élite dentro del ABC— no aparece documentada en la
revisión realizada, lo que sugiere una línea de investigación abierta.

## A.9. Alcance, limitaciones y trabajo futuro

Los resultados de este anexo son **diagnósticos exploratorios y no reemplazan los
resultados congelados de la tesis**. Tres salvedades: la evaluación es dentro de la muestra,
sobre las mismas ventanas del estudio; las configuraciones activadas usan valores por
defecto sin calibración dedicada; y el Sharpe deflactado se calculó frente a las
configuraciones examinadas, no frente al espacio completo de diseño. Además, las cifras de
este anexo emplean el Sortino medio por semilla (necesario para las pruebas pareadas), que
difiere del *best-of-seeds* reportado en las tablas canónicas del cuerpo principal.

El paso confirmatorio natural es una validación *walk-forward* fuera de muestra sobre el
panel histórico completo, con calibración dedicada del parámetro de concentración y del
umbral de activación, incorporación de costos de transacción y universos de mayor tamaño.
Ese programa excede el alcance de este trabajo de grado y se plantea como línea futura, en
continuidad directa con el comentario del jurado: la limitación identificada en el
mecanismo de scout no solo quedó documentada y explicada, sino que se transformó en un
diseño instrumentado, medido y reproducible que abre una vía concreta de mejora para la
familia de algoritmos propuesta.

## Referencias

André, E., y Coqueret, G. (2020). *Dirichlet policies for reinforced factor portfolios*
[preprint]. arXiv:2011.05381.

Bailey, D. H., y López de Prado, M. (2014). The deflated Sharpe ratio: Correcting for
selection bias, backtest overfitting, and non-normality. *The Journal of Portfolio
Management*, 40(5), 94–107.

Bullinaria, J. A., y AlYahya, K. (2014). Artificial Bee Colony training of neural
networks. En G. Terrazas, F. E. B. Otero y A. D. Masegosa (Eds.), *Nature Inspired
Cooperative Strategies for Optimization (NICSO 2013)* (Studies in Computational
Intelligence, Vol. 512, pp. 191–201). Springer.

Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian
Journal of Statistics*, 6(2), 65–70.

Hussain, K., Mohd Salleh, M. N., Cheng, S., Shi, Y., y Naseem, R. (2020). Artificial bee
colony algorithm: A component-wise analysis using diversity measurement. *Journal of
King Saud University – Computer and Information Sciences*, 32(7), 794–808.

Karaboga, D. (2005). *An idea based on honey bee swarm for numerical optimization*
(Technical Report TR-06). Erciyes University.

Le Courtois, O., y Xu, X. (2024). Efficient portfolios and extreme risks: A
Pareto–Dirichlet approach. *Annals of Operations Research*, 335(1), 261–292.

Singh, A., y Deep, K. (2019). Exploration–exploitation balance in Artificial Bee Colony
algorithm: A critical analysis. *Soft Computing*, 23, 9525–9536.

Tuba, M., y Bacanin, N. (2014). Artificial bee colony algorithm hybridized with firefly
algorithm for cardinality-constrained mean-variance portfolio selection. *Applied
Mathematics and Information Sciences*, 8(6), 2791–2801.

Yang, H., Park, H., y Lee, K. (2022). A selective portfolio management algorithm with
off-policy reinforcement learning using Dirichlet distribution. *Axioms*, 11(12), 664.

Yang, X.-S. (2009). Firefly algorithms for multimodal optimization. En *Stochastic
Algorithms: Foundations and Applications (SAGA 2009)* (Lecture Notes in Computer Science,
Vol. 5792, pp. 169–178). Springer.
