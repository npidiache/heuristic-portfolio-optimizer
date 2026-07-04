"""
ABC-FA-Scout Algorithm - Prototipo de Tesis (Refactorizado)
===========================================================

Implementación del novedoso algoritmo híbrido ABC-FA-Scout, utilizando
herencia para una estructura de código limpia y clara.

INNOVACIÓN CLAVE:
- La clase `ABC_FA_Scout` hereda toda la funcionalidad de `ABC_BeeHive`.
- Se sobrescribe únicamente el método `send_scout` para implementar la
  búsqueda inteligente guiada por el Algoritmo de la Luciérnaga (FA),
  que es el núcleo de la propuesta de investigación.
"""

import math
import random
from .abc_original import ABC_BeeHive, Bee

class ABC_FA_Scout(ABC_BeeHive):
    """
    Hereda de ABC_BeeHive y sobrescribe la fase de la exploradora.
    """
    def __init__(self, *args, **kwargs):
        # Extraer parámetros específicos del FA-Scout antes de llamar al constructor padre
        self.b0 = kwargs.pop('b0', 1.0)
        self.gamma = kwargs.pop('gamma', 1.0)
        self.alpha = kwargs.pop('alpha', 0.2)
        # Parámetros de líder robusto (top-k con softmax por fitness)
        self.k_top = kwargs.pop('k_top', 3)
        self.softmax_tau = kwargs.pop('softmax_tau', 1.0)
        
        # Llamar al constructor de la clase padre (ABC_BeeHive)
        super().__init__(*args, **kwargs)

    def send_scout(self):
        """
        FASE MODIFICADA: Abeja exploradora guiada por FA (FA-Scout).
        
        Esta función sobrescribe el `send_scout` de la clase `ABC_BeeHive`.
        """
        trials = [bee.counter for bee in self.population]
        # Encontrar el índice de la abeja con el máximo número de intentos
        try:
            index = trials.index(max(trials))
        except ValueError:
            return # No hay nada que hacer si la lista está vacía

        if trials[index] > self.max_trials:
            # --- INICIO del Mecanismo FA-Scout ---
            scout_bee = self.population[index]
            
            # Selección robusta del líder: samplear entre top-k por fitness usando softmax
            try:
                sorted_bees = sorted(self.population, key=lambda b: b.fitness, reverse=True)
                k = max(1, min(self.k_top, len(sorted_bees)))
                candidates = sorted_bees[:k]
                # Softmax estable: restar el máximo y escalar por temperatura
                max_fit = candidates[0].fitness
                tau = self.softmax_tau if self.softmax_tau > 1e-12 else 1.0
                weights = [math.exp((b.fitness - max_fit) / tau) for b in candidates]
                sum_w = sum(weights)
                if sum_w <= 0 or not math.isfinite(sum_w):
                    # Fallback: distribución uniforme sobre top-k
                    probs = [1.0 / k] * k
                else:
                    probs = [w / sum_w for w in weights]
                # Muestreo con roulette usando el RNG del algoritmo
                u = self.rng.random()
                acc = 0.0
                selected = candidates[-1]
                for cand, p in zip(candidates, probs):
                    acc += p
                    if u <= acc:
                        selected = cand
                        break
                target_vector = selected.vector
            except Exception:
                # Fallback conservador: mejor abeja
                best_bee = max(self.population, key=lambda bee: bee.fitness)
                target_vector = best_bee.vector

            # 1. Calcular distancia euclidiana al objetivo
            r = math.sqrt(sum((s_v - t_v) ** 2 for s_v, t_v in 
                             zip(scout_bee.vector, target_vector)))

            new_vector = [0.0] * self.dim
            # 2. Aplicar ecuación de movimiento FA para cada dimensión
            for d in range(self.dim):
                scout_val = scout_bee.vector[d]
                target_val = target_vector[d]
                rand_val = self.rng.random()
                
                # Ecuación de movimiento del FA
                attraction = self.b0 * math.exp(-self.gamma * (r ** 2)) * (target_val - scout_val)
                random_term = self.alpha * (rand_val - 0.5)
                
                new_vector[d] = scout_val + attraction + random_term
            
            scout_bee.vector = self._check(new_vector)
            scout_bee.value = self.evaluate(scout_bee.vector)
            scout_bee._fitness()
            scout_bee.counter = 0

            # --- FIN del Mecanismo FA-Scout --- 