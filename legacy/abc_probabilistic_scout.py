"""
ABC-Probabilistic-Scout Algorithm
================================

Implementación del algoritmo híbrido ABC con fase de exploradora basada en
estrategia ε-greedy probabilística, utilizando herencia para una estructura de código limpia.

INNOVACIÓN CLAVE:
- La clase `ABC_Probabilistic_Scout` hereda toda la funcionalidad de `ABC_BeeHive`.
- Se sobrescribe únicamente el método `send_scout` para implementar la
  estrategia ε-greedy que balancea exploración y explotación.
"""

import random
from .abc_original import ABC_BeeHive, Bee

class ABC_Probabilistic_Scout(ABC_BeeHive):
    """
    Hereda de ABC_BeeHive y sobrescribe la fase de la exploradora con una
    estrategia ε-greedy (épsilon-greedy).
    """
    def __init__(self, *args, **kwargs):
        # Extraer el parámetro específico del explorador probabilístico
        self.epsilon = kwargs.pop('epsilon', 0.1) # 10% de exploración pura
        
        # Llamar al constructor de la clase padre (ABC_BeeHive)
        super().__init__(*args, **kwargs)

    def send_scout(self):
        """
        FASE MODIFICADA: Abeja exploradora con decisión probabilística.
        
        La abeja estancada decide si hacer una exploración puramente aleatoria
        (con probabilidad epsilon) o una búsqueda guiada hacia la mejor
        solución global (con probabilidad 1 - epsilon).
        """
        trials = [bee.counter for bee in self.population]
        try:
            index = trials.index(max(trials))
        except ValueError:
            return

        if trials[index] > self.max_trials:
            # --- INICIO del Mecanismo del Explorador Probabilístico ---
            
            # 1. El "Instinto": Decisión probabilística ε-greedy
            if self.rng.random() < self.epsilon:
                # 2.A. Exploración Pura (comportamiento del ABC original)
                # Garantiza que el algoritmo nunca deje de explorar zonas nuevas.
                self.population[index] = Bee(self.lower, self.upper, self.evaluate, rng=self.rng)
                self.population[index].counter = 0
                return

            else:
                # 2.B. Búsqueda Guiada (hacia la mejor solución global)
                # Usa la inteligencia colectiva para buscar en zonas prometedoras.
                scout_bee = self.population[index]
                target_vector = self.solution

                if target_vector is None: # Fallback si no hay solución aún
                    self.population[index] = Bee(self.lower, self.upper, self.evaluate, rng=self.rng)
                    self.population[index].counter = 0
                    return

                new_vector = [0.0] * self.dim
                phi = self.rng.random() # Un único factor de escala para el movimiento

                # Aplicar ecuación de movimiento simple para cada dimensión
                for d in range(self.dim):
                    scout_val = scout_bee.vector[d]
                    target_val = target_vector[d]
                    
                    # Movimiento guiado hacia la vecindad del mejor global
                    new_vector[d] = scout_val + phi * (target_val - scout_val)
                
                # Actualizar la abeja scout directamente
                scout_bee.vector = self._check(new_vector)
                scout_bee.value = self.evaluate(scout_bee.vector)
                scout_bee._fitness()
                scout_bee.counter = 0
            # --- FIN del Mecanismo --- 