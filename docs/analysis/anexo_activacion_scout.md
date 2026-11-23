# Anexo A. Diagnóstico y rediseño del mecanismo explorador en el algoritmo ABC

*Versión en inglés: [`annex_scout_activation.md`](annex_scout_activation.md).*

> Este anexo presenta un análisis diagnóstico complementario sobre la activación del
> mecanismo explorador (*scout*) y una línea de extensión basada en un reinicio de
> Dirichlet. Las cifras de activación y desempeño se obtienen mediante ejecuciones
> reproducibles sobre los datos y las convenciones metodológicas de la tesis. Los
> resultados, parámetros y conclusiones del cuerpo principal permanecen inalterados.
>
> Esta es una versión extendida del Anexo A de la tesis aprobada. Las secciones A.1 a
> A.4 desarrollan el diagnóstico de activación incluido en la tesis; las secciones A.5
> en adelante (geometría del muestreo, reinicio de Dirichlet y límites de concentración)
> corresponden a trabajo exploratorio posterior a la aprobación, realizado por Norbey
> Pidiache.

## A.1. Motivación y alcance de la mejora incremental

El punto de partida de esta investigación es el desempeño del algoritmo ABC original,
que supera consistentemente a los referentes clásicos —la optimización media-varianza
(PMVG) y la asignación equiponderada (1/N)— en el ratio de Sortino para todos los
regímenes de volatilidad analizados. Este resultado sustenta la hipótesis central de la
tesis y se conserva sin modificaciones.

Sobre esa base, el trabajo persigue una mejora incremental. El ABC tiene limitaciones
conocidas en su capacidad de explotación local; para atacarlas se evaluó primero el
ABC-FA de Tuba y Bacanin (2014), que inserta un movimiento tipo luciérnaga en la fase de
abejas empleadas. En los escenarios de este estudio, sin embargo, esa variante no ofrece
un buen desempeño (su mecanismo sí se ejecuta, y aun así queda por debajo del ABC
original). Ante ese resultado, la tesis propone alterar específicamente la **fase
exploradora** (*scout*) del ABC —mediante un disparador probabilístico (PFA), una
atracción guiada por élites (ABC-FAEM) y una atracción gravitacional (ABC-GSA)— con el
objetivo de superar las limitaciones del original. Estas variantes se entienden como
propuestas de mejora sujetas a verificación empírica.

El diagnóstico que motiva este anexo muestra que, dada la dimensionalidad del problema,
los mecanismos asociados a la fase exploradora no llegan a ejecutarse bajo la
configuración calibrada. A partir de este hallazgo se plantean dos preguntas: (i) ¿cómo
lograr que el explorador se active? y (ii) ¿qué efecto produce su activación sobre el
desempeño?

## A.2. Inactividad del explorador bajo la calibración

El umbral de abandono se deriva de forma proporcional a la dimensión, `max_trials = 0.6 ×
25 abejas × 20 activos = 300`. Pero el contador de intentos de una abeja solo crece cuando
un movimiento no mejora su fuente, y dentro del presupuesto de 60 iteraciones dicho
contador alcanza un máximo observado cercano a **19**. Ninguna abeja supera el umbral de
300 y la fase exploradora **no se ejecuta en ninguna de las configuraciones evaluadas**
(ambos universos, cuatro regímenes y 20 semillas). Dado que las variantes redefinen
exclusivamente el movimiento del explorador, las diferencias observadas entre el ABC
original, el ABC-FAEM y el ABC-GSA bajo esta calibración provienen de sus trayectorias
estocásticas, no de la intervención efectiva de dicho mecanismo.

## A.3. Instrumentación: telemetría de activación

Para pasar de la inferencia indirecta a la medición directa, se instrumentó cada ejecución
con el número de activaciones del explorador y las iteraciones en que ocurren. El Cuadro
A.1 reporta las activaciones medias por ejecución (ambos universos) para la configuración
calibrada y para umbrales de activación proporcionales al presupuesto de iteraciones.

**Cuadro A.1. Activaciones medias del explorador por ejecución.**

| Configuración | COVID-19 | Crisis 2007–09 | Guerra | Estabilidad |
| --- | ---: | ---: | ---: | ---: |
| ABC original (calibrado) | 0.0 | 0.0 | 0.0 | 0.0 |
| ABC-GSA con umbral canónico (`max_trials`=300) | 0.0 | 0.0 | 0.0 | 0.0 |
| ABC-GSA activo (`max_trials`=9) | 10.9 | 9.9 | 9.8 | 10.4 |
| ABC-FAEM activo (`max_trials`=9) | 12.4 | 11.7 | 11.3 | 11.9 |
| Reinicio de Dirichlet élite (fracción 0.15) | 12.3 | 13.1 | 10.9 | 12.3 |

Bajo la calibración, el mecanismo permanece inactivo. Un umbral proporcional al horizonte
lo vuelve operativo a una tasa controlada (~10-13 activaciones por ejecución, cerca del
0,4% de las ~3.100 evaluaciones de la función objetivo).

## A.4. Desempeño de los mecanismos bajo activación

La evaluación del efecto de la activación exige emplear semillas idénticas entre
configuraciones, de modo que las comparaciones estadísticas sean efectivamente pareadas.
El Cuadro A.2 presenta el Sortino medio por semilla, agregado sobre las ocho celdas
régimen–universo.

**Cuadro A.2. Sortino medio por semilla (agregado, 8 celdas).**

| Configuración | Sortino medio |
| --- | ---: |
| Reinicio de Dirichlet élite f=0.15 *(posterior a la tesis, sin límite de concentración; ver A.6–A.7)* | **2.870** |
| ABC original | 2.145 |
| ABC-GSA con umbral canónico (inactivo) | 1.975 |
| ABC-FAEM activo mt=9 | 1.964 |
| ABC-GSA activo mt=9 | 1.860 |
| PMVG (media-varianza) | 1.161 |
| 1/N (equiponderado) | 0.920 |

Los resultados permiten establecer tres conclusiones:

- **Mejora marginal.** Al activar la atracción por luciérnagas (ABC-FAEM mt=9), el
  desempeño apenas se distingue del ABC original y presenta variaciones inconsistentes
  entre regímenes, como ya anticipaba el diagnóstico proporcional previo
  ([`faem_activation_calibration.md`](faem_activation_calibration.md)).
- **Deterioro bajo atracción gravitacional.** Al activar la atracción gravitacional
  (ABC-GSA mt=9), el desempeño queda por debajo del ABC original en las ocho celdas y la
  diferencia conserva significancia tras la corrección de Holm en seis de ellas,
  incluidas las de baja volatilidad (estabilidad). Este comportamiento, presente en
  distintos regímenes y universos, se analiza en la sección A.5.
- **Preservación de la hipótesis central.** El menor desempeño se produce frente al ABC
  original, no frente a los referentes clásicos. Incluso el caso menos favorable
  (ABC-GSA activo, 1.860) permanece por encima de PMVG (1.161) y de 1/N (0.920). Por
  tanto, la activación redistribuye el desempeño dentro de la familia bioinspirada sin
  transferir la ventaja a los métodos clásicos.

**Cuadro A.3. ABC-GSA activo frente a ABC original, por celda (Δ = GSA activo − ABC original).**

| Régimen | Δ universo fijo | Δ universo dinámico |
| --- | ---: | ---: |
| COVID-19 (crisis) | −0.537 (significativo tras Holm) | −0.462 (significativo tras Holm) |
| Crisis financiera global de 2008 | −0.055 (significativo) | −0.042 (no significativo) |
| Guerra 2022 (volatilidad alta) | −0.341 (significativo tras Holm) | −0.254 (significativo tras Holm) |
| Estabilidad 2023–24 (volatilidad baja) | −0.236 (significativo tras Holm) | −0.352 (significativo tras Holm) |

## A.5. El problema de fondo: el sesgo de normalización y la geometría

Los dos hallazgos de la sección A.4 —la activación por sí sola no garantiza una mejora y
los movimientos definidos en el espacio de caja pueden deteriorar el desempeño— apuntan
a una causa común de naturaleza geométrica.

El conjunto de portafolios factibles de solo posiciones largas (*long-only*) —vectores de
pesos no negativos que suman uno— constituye el **símplex de probabilidad**: un objeto
cuyos vértices representan la concentración total en un único activo, cuyo baricentro
corresponde a la asignación equiponderada (1/N) y cuyas aristas y caras corresponden a
portafolios que emplean solo un subconjunto de los activos (Figura A.1). Los movimientos
de recuperación que operan en el **espacio de caja** —el reinicio aleatorio uniforme, el
desplazamiento tipo luciérnaga o
la atracción gravitacional del ABC-GSA— generan candidatos que en general no pertenecen a
este conjunto y exigen una **renormalización posterior** (dividir por la suma de pesos).
Esta operación introduce un sesgo al distorsionar la perturbación pretendida. Además, el
ABC-GSA dirige el movimiento hacia el centro de masa del enjambre —una solución de
consenso que no necesariamente pertenece a la región de mejor desempeño— en lugar de
orientarlo hacia las soluciones élite. La combinación de ambos efectos explica el
deterioro observado tras su activación.

La pregunta natural es entonces: ¿cómo superar el sesgo de normalización? La respuesta que
propone la extensión es recomponer la solución **directamente sobre el símplex**, sin pasar
por el espacio de caja.

## A.6. Línea de extensión: reinicio de Dirichlet nativo del símplex

> Esta sección presenta una **extensión metodológica** y no modifica los resultados del
> cuerpo principal de la tesis.

Se propone un operador de reinicio que, cuando una abeja se estanca, la recompone mediante
una muestra de una **distribución de Dirichlet concentrada alrededor de la dirección
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
luciérnaga (centro) apenas desplaza la abeja de su posición estancada; el reinicio de
Dirichlet propuesto (derecha) concentra los candidatos alrededor de la dirección media
de las soluciones élite, generando portafolios factibles por construcción.

En la evaluación con semillas pareadas, el reinicio de Dirichlet (fracción 0.15) eleva el
Sortino medio por semilla de 2.145 (ABC original) a **2.870**, y obtiene además el mejor
valor medio de la función objetivo ejecutada, lo que indica que encuentra mejores
soluciones para el objetivo optimizado y no simplemente valores más favorables de la
métrica de evaluación. Las pruebas de Wilcoxon frente al ABC original, corregidas con el
procedimiento de Holm (1979)
dentro de cada celda, resultan significativas y favorables a Dirichlet élite en **las ocho
celdas** régimen–universo; ninguna otra configuración examinada presenta superioridad en
una celda después de la corrección.

Como control adicional frente a la selección, el ratio de Sharpe deflactado (DSR; Bailey
y López de Prado, 2014) del mejor portafolio del operador supera 0,95 en cuatro de las
ocho celdas —COVID-19 y estabilidad, en ambos universos, con valores de hasta 0,9998—,
pero se sitúa entre 0,51 y 0,72 durante la crisis financiera global y la guerra. En
consecuencia, la superioridad *relativa* del operador frente al ABC original conserva
significancia tras el control por comparaciones múltiples en todas las celdas, mientras
que la evidencia *absoluta* de desempeño distinguible del azar se establece
específicamente en las celdas de COVID-19 y estabilidad.

**Cuadro A.4. Sharpe deflactado del mejor portafolio de Dirichlet élite (variante sin
restricción de concentración).**

| Régimen | Universo fijo | Universo dinámico |
| --- | ---: | ---: |
| COVID-19 (2020) | **0.9832** | **0.9801** |
| Crisis financiera global (2007–09) | 0.6467 | 0.5095 |
| Guerra (2022) | 0.6804 | 0.7208 |
| Estabilidad (2023–24) | **0.9998** | **0.9997** |

*Nota.* Los valores en negrita alcanzan el umbral de referencia DSR ≥ 0.95.

Estas cifras, sin embargo, exigen un examen del perfil de concentración de los portafolios
obtenidos. La sección A.7 aborda ese examen y conduce a una revisión sustantiva de la
magnitud del efecto atribuible al operador.

## A.7. Robustez del operador bajo límites de concentración

El desempeño superior documentado en la sección A.6 requiere verificar *cómo* se obtiene.
El Cuadro A.5 compara el perfil de concentración de los portafolios finales del ABC
original y del reinicio de Dirichlet en el universo de fundamentales.

**Cuadro A.5. Concentración de los portafolios finales (promedio de 20 semillas,
universo de fundamentales).**

| Régimen | Modelo | Posiciones &gt;1 % | Cardinalidad efectiva | Peso máximo |
| --- | --- | ---: | ---: | ---: |
| COVID-19 | ABC original | 8.8 | 6.0 | 23 % |
| | Dirichlet | 4.4 | **2.1** | **68 %** |
| Crisis 2007–09 | ABC original | 6.9 | 5.4 | 23 % |
| | Dirichlet | 3.1 | **2.2** | **60 %** |
| Guerra 2022 | ABC original | 9.5 | 7.4 | 17 % |
| | Dirichlet | 5.1 | **2.6** | **55 %** |
| Estabilidad | ABC original | 9.0 | 6.6 | 21 % |
| | Dirichlet | 4.9 | **2.1** | **65 %** |

Los portafolios del operador no son más equilibrados que los del ABC original: son
sustancialmente **más concentrados**. Una cardinalidad efectiva cercana a 2 y un peso
máximo superior al 55 % describen una posición concentrada en uno o dos activos, no una
cartera diversificada.

Este comportamiento tiene una explicación directa. La Ec. 18 está orientada a controlar el
exceso de diversificación —penaliza más de diez posiciones significativas, en línea con su
propósito de diseño— y, dentro del contexto original de la tesis, no requiere un límite de
concentración adicional: los algoritmos evaluados operan en el espacio de caja y sus
candidatos no superan pesos máximos cercanos al 20 %. El operador de Dirichlet, en cambio,
posee un **alcance exploratorio mayor**: accede a portafolios concentrados que la búsqueda
original no visita, y lo hace optimizando correctamente la función objetivo (de hecho
alcanza mejores valores que el ABC original). Una comparación rigurosa entre ambos exige,
por tanto, incorporar un límite de concentración del tipo empleado habitualmente en
mandatos institucionales, de manera que los dos algoritmos compitan sobre el mismo
conjunto de portafolios admisibles.

Para determinar si la ventaja del operador subsiste bajo dicho límite se evaluaron dos
restricciones, aplicadas por igual a ambos modelos y bajo semillas pareadas idénticas:

1. **Piso de cardinalidad (mínimo cinco posiciones significativas).** Se añadió el término
   simétrico `λ_card · max(0, 5 − posiciones)²`. La restricción resultó **insuficiente**:
   el operador la satisface manteniendo un peso máximo del 56 % y una cardinalidad efectiva
   de 2.6, es decir, cinco posiciones nominales de las cuales una concentra más de la
   mitad del capital. Contar posiciones por encima de un umbral no controla la magnitud de
   los pesos.
2. **Tope duro de peso máximo (20 %).** Se impuso mediante proyección de los pesos
   normalizados sobre el símplex acotado, garantizando que todo portafolio evaluado cumple
   la restricción; con veinte activos, el tope implica al menos cinco posiciones
   materialmente relevantes. Esta es la restricción que efectivamente controla la
   concentración.

**Cuadro A.6. Efecto de las restricciones de concentración sobre la ventaja del operador.**

| Escenario | Dirichlet | ABC original | Diferencia | Card. efectiva | Peso máximo | Celdas favorables tras Holm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Sin restricción | 2.870 | 2.145 | +0.726 | 2.4 | 59 % | 8 de 8 |
| Piso de cinco posiciones | 2.832 | 2.145 | +0.687 | 2.6 | 56 % | 8 de 8 |
| **Tope duro de 20 %** | **2.387** | **2.102** | **+0.285** | **5.6** | **20 %** | **7 de 8** |

*Nota.* Sortino medio por semilla, agregado sobre las ocho celdas régimen–universo. El
tope de 20 % también actúa sobre el ABC original —su peso máximo desciende de 0.20 a
0.18—, por lo que la comparación conserva condiciones idénticas.

La lectura correcta de estos resultados es doble. Por una parte, **aproximadamente el 60 %
de la ventaja inicial era atribuible a la concentración**: la diferencia de +0.726 se
reduce a +0.285 al acotar el peso máximo. Por otra, **la ventaja restante es robusta**: con
la concentración efectivamente controlada (cardinalidad efectiva 5.6 y peso máximo 20 %),
el operador conserva una mejora de +0.285 en el Sortino medio, favorable en las ocho celdas
y estadísticamente significativa tras la corrección de Holm en siete de ellas, sin ninguna
celda desfavorable. En la crisis financiera global del universo dinámico, el operador
reduce el Sortino negativo del ABC original (−0.292) prácticamente a cero (−0.007).

En consecuencia, la contribución defendible del operador no es la magnitud inicialmente
observada, sino una mejora de búsqueda que **subsiste bajo una restricción de concentración
de tipo institucional**. El ejercicio deja además una recomendación práctica: los
operadores con mayor alcance exploratorio deben acompañarse de un límite explícito de
concentración —como es habitual en mandatos institucionales—, de manera que la ganancia de
búsqueda se materialice dentro del perfil de diversificación deseado por el gestor.

## A.8. Un procedimiento generalizable de diagnóstico y rediseño

El aporte de esta línea no es un movimiento de recuperación en particular, sino un
**procedimiento** aplicable a cualquier mecanismo explorador: registrar su activación
como una variable observable, emplear un umbral proporcional al horizonte, medir su
efecto mediante estadística pareada, rediseñar el movimiento cuando la geometría del
espacio de soluciones condicione el valor de la recuperación y —como muestra la sección
A.7— **verificar la robustez de la mejora bajo límites de concentración**, de modo que la
ganancia atribuida al operador se sostenga dentro del perfil de portafolio deseado. El
reinicio de Dirichlet constituye la
aplicación de este procedimiento al problema *long-only*. En este sentido, la extensión
generaliza el trabajo de la tesis sin reemplazar sus resultados principales.

## A.9. Relación con la literatura

El fenómeno de un operador explorador inactivo bajo la calibración empleada no es
exclusivo de este trabajo. Bullinaria y AlYahya (2014) observaron empíricamente que, con
la calibración predeterminada del ABC, la fase *scout* prácticamente no se activa y la
declararon redundante mediante ablación sobre el umbral de abandono. Singh y Deep (2019)
llegaron a una conclusión afín sobre el balance exploración-explotación del ABC, señalando
que el explorador puede volverse redundante en alta dimensión. Hussain et al. (2020),
mediante un análisis componente a componente basado en diversidad, reportan igualmente
que este componente puede aportar poco al desempeño. La contribución de este anexo
respecto de esa línea es doble: instrumentar la activación vinculada a una función
objetivo financiera y, a diferencia de los trabajos que se concentran en el diagnóstico,
vincular la auditoría con un rediseño que recupera valor.

El uso de la distribución de Dirichlet para representar pesos de portafolios *long-only*
sobre el símplex está establecido en la literatura financiera (André y Coqueret, 2020;
Yang, Park y Lee, 2022; Le Courtois y Xu, 2024), aunque en contextos de aprendizaje por
refuerzo o de construcción directa del conjunto eficiente, y no como operador dentro de una
metaheurística. La combinación específica —disparador por estancamiento, muestreo nativo
al símplex y condicionamiento a la media élite dentro del ABC— no aparece documentada en la
revisión realizada, lo que sugiere una línea de investigación abierta.

## A.10. Alcance, limitaciones y trabajo futuro

Los resultados de este anexo corresponden a un **diagnóstico exploratorio
complementario**. La interpretación debe considerar tres limitaciones: (i) la evaluación
se realiza dentro de muestra y sobre las mismas ventanas del estudio; (ii) las
configuraciones activadas emplean valores predeterminados sin una calibración específica;
y (iii) el Sharpe deflactado se calcula frente a las configuraciones examinadas, no frente
al espacio completo de diseño, y corresponde a la variante sin restricción de
concentración. Además, las cifras emplean el Sortino medio por semilla, necesario para las
pruebas pareadas, que difiere del criterio *best-of-seeds* reportado en las tablas del
cuerpo principal.

El paso confirmatorio natural es una validación *walk-forward* fuera de muestra sobre el
panel histórico completo, tomando como hipótesis la formulación depurada en la sección
A.7 —el reinicio de Dirichlet con tope de concentración del 20 %— e incorporando
calibración dedicada del parámetro de concentración y del umbral de activación, costos de
transacción y universos de mayor tamaño. Este programa excede el alcance del trabajo de
grado y se plantea como línea futura. La limitación identificada en el mecanismo explorador
queda así documentada, medida y explicada, y se traduce en un diseño reproducible cuyo
efecto ha sido cuantificado y depurado de su componente de concentración, lo que abre una
vía concreta de mejora para la familia de algoritmos propuesta.

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
