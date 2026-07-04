"""
ABC-FA Algorithm Implementation (Bacanin et al.)
==============================================

CORRECCION: Implementación fiel del algoritmo ABC-FA propuesto por Bacanin et al.
con los parámetros correctos y la hibridación apropiada.

Paper: "A hybrid algorithm based on artificial bee colony and firefly algorithm 
for global optimization" (Bacanin et al.)

DIFERENCIAS CON ABC ESTÁNDAR:
- Employed bees: Usa ecuación de movimiento de Firefly
- Scout bees: Mantiene búsqueda aleatoria tradicional
- Parámetros FA: b0=1.1, gamma=1.4, alpha=0.025 (según paper)
"""

import random
import copy
import math
import sys
import numpy as np
from typing import Optional, Dict, Any, List, Callable

class Bee:
    """
    Clase individual Bee (abeja) que representa una solución candidata
    """
    def __init__(self, lower: List[float], upper: List[float], 
                 fun: Optional[Callable] = None, funcon: Optional[Callable] = None,
                 rng: Optional[random.Random] = None):
        self.rng = rng if rng else random.Random()
        self._random(lower, upper)
        self.valid = True if not funcon else funcon(self.vector)
        self.value = fun(self.vector) if fun else sys.float_info.max
        self._fitness()
        self.counter = 0  # Contador de trials sin mejora

    def _random(self, lower: List[float], upper: List[float]):
        """Genera solución aleatoria dentro de bounds"""
        self.vector = [lower[i] + self.rng.random() * (upper[i] - lower[i]) 
                      for i in range(len(lower))]

    def _fitness(self):
        """Calcula fitness basado en el valor de la función objetivo"""
        if self.value >= 0:
            self.fitness = 1 / (1 + self.value)
        else:
            self.fitness = 1 + abs(self.value)

class ABC_FA_Bacanin:
    """
    ABC-FA Algorithm (Bacanin et al.) - Implementación Corregida
    ==========================================================
    
    Hibridación entre Artificial Bee Colony y Firefly Algorithm:
    - Employed bees: Usan ecuación de movimiento Firefly
    - Onlooker bees: Siguen a employed bees exitosos 
    - Scout bees: Búsqueda aleatoria tradicional
    """
    
    def __init__(self, 
                 lower: List[float], 
                 upper: List[float],
                 fun: Optional[Callable] = None,
                 numb_bees: int = 50,
                 max_itrs: int = 200,
                 max_trials: Optional[int] = None,
                 seed: Optional[int] = 42,
                 verbose: bool = False,
                 # PARÁMETROS CORREGIDOS SEGÚN BACANIN
                 b0: float = 1.1,      # ✅ Attractiveness at r=0
                 gamma: float = 1.4,   # ✅ Light absorption coefficient  
                 alpha: float = 0.025  # ✅ Randomization factor
                ):
        
        # Validación de entrada
        assert len(upper) == len(lower), "'lower' and 'upper' must be same length."
        
        # Configuración de semilla con derivación única por algoritmo
        base_seed = seed if seed else random.randint(0, 1000)
        # Crear semilla derivada única para este algoritmo
        algorithm_hash = hash(self.__class__.__name__) % 1000000
        derived_seed = (base_seed * 1000 + algorithm_hash) % (2**31 - 1)
        
        self.seed = base_seed  # Guardar semilla original para referencia
        self.derived_seed = derived_seed
        self.rng = random.Random(derived_seed)  # Usar semilla derivada
        
        # Parámetros del algoritmo
        self.size = int(numb_bees + numb_bees % 2)  # Número par de abejas
        self.dim = len(lower)
        self.max_itrs = max_itrs
        self.max_trials = max_trials if max_trials else int(0.6 * self.size * self.dim)
        self.verbose = verbose
        
        # PARÁMETROS FA CORREGIDOS
        self.b0 = b0        # ✅ 1.1 (no 1.0)
        self.gamma = gamma  # ✅ 1.4 (no 1.0)  
        self.alpha = alpha  # ✅ 0.025 (no 0.2)
        
        # Configuración del problema
        self.evaluate = fun
        self.lower = lower
        self.upper = upper
        self.best = sys.float_info.max
        self.solution = None
        
        # Inicializar población con generador específico
        self.population = [Bee(lower, upper, fun, rng=self.rng) for _ in range(self.size)]

        # RESTAURACIÓN: Llamar a find_best() y compute_probability() es crucial.
        # Esto asegura que todos los atributos necesarios, incluyendo .probas,
        # se inicialicen correctamente antes de la ejecución.
        self.find_best()
        self.compute_probability()

    def run(self) -> Dict[str, List[float]]:
        """
        Ejecuta el algoritmo ABC-FA completo
        """
        cost = {"best": [], "mean": []}
        
        for itr in range(self.max_itrs):
            # Fase 1: Employed Bees (con hibridación FA)
            for index in range(self.size):
                self.send_employee(index)
            
            # Fase 2: Onlooker Bees  
            self.send_onlookers()
            
            # Fase 3: Scout Bees (tradicional)
            self.send_scout()
            
            # Actualizar mejor solución
            self.find_best()
            
            # Guardar estadísticas
            cost["best"].append(self.best)
            cost["mean"].append(sum(bee.value for bee in self.population) / self.size)
            
            if self.verbose:
                self._verbose(itr, cost)
        
        return cost

    def send_employee(self, index: int):
        """
        HIBRIDACIÓN FA-ABC: Employed bees usan ecuación de movimiento Firefly
        
        Ecuación FA: x_i^new = x_i + β₀ * e^(-γr²) * (x_k - x_i) + α * (rand - 0.5)
        Donde:
        - β₀ = attractiveness at r=0 (b0)
        - γ = light absorption coefficient (gamma)  
        - α = randomization factor (alpha)
        - r = Euclidean distance entre x_i y x_k
        """
        zombee = copy.deepcopy(self.population[index])
        
        # Seleccionar otra abeja aleatoria
        bee_ix = index
        while bee_ix == index:
            bee_ix = self.rng.randint(0, self.size - 1)
        
        # CLAVE: Calcular distancia euclidiana (componente FA)
        r = math.sqrt(sum((xi - xk) ** 2 for xi, xk in 
                         zip(self.population[index].vector,
                             self.population[bee_ix].vector)))
        
        # HIBRIDACIÓN FA: Aplicar ecuación FA a TODAS las dimensiones
        for d in range(self.dim):
            x_i = self.population[index].vector[d]
            x_k = self.population[bee_ix].vector[d]
            rand_val = self.rng.random()
            
            # ECUACIÓN FA CORREGIDA
            new_val = (x_i + 
                      self.b0 * math.exp(-self.gamma * (r ** 2)) * (x_k - x_i) + 
                      self.alpha * (rand_val - 0.5))
            
            zombee.vector[d] = new_val
        
        # Verificar bounds
        zombee.vector = self._check(zombee.vector)
        
        # Evaluar nueva solución
        zombee.value = self.evaluate(zombee.vector)
        zombee._fitness()
        
        # Greedy selection
        if zombee.fitness > self.population[index].fitness:
            self.population[index] = copy.deepcopy(zombee)
            self.population[index].counter = 0
        else:
            self.population[index].counter += 1

    def send_onlookers(self):
        """
        Fase de Onlooker bees: siguen a employed bees con probabilidad proporcional a fitness
        """
        numb_onlookers = 0
        beta = 0
        
        while numb_onlookers < self.size:
            phi = self.rng.random()
            beta += phi * max(self.probas)
            beta %= max(self.probas)
            index = self.select(beta)
            self.send_employee(index)  # Reutiliza la misma lógica FA
            numb_onlookers += 1

    def send_scout(self):
        """
        TRADICIONAL: Scout bees realizan búsqueda aleatoria (sin hibridación FA)
        """
        trials = [self.population[i].counter for i in range(self.size)]
        index = trials.index(max(trials))
        
        if trials[index] > self.max_trials:
            # Scout tradicional: solución completamente aleatoria
            self.population[index] = Bee(self.lower, self.upper, self.evaluate, rng=self.rng)
            self.population[index].counter = 0

    def find_best(self):
        """Encuentra la mejor solución en la población actual"""
        values = [bee.value for bee in self.population]
        index = values.index(min(values))
        
        if self.population[index].value < self.best:
            self.best = self.population[index].value
            self.solution = copy.deepcopy(self.population[index].vector)

    def compute_probability(self):
        """Calcula probabilidades de selección para onlooker bees"""
        fitness_sum = sum(bee.fitness for bee in self.population)
        self.probas = [bee.fitness / fitness_sum for bee in self.population]
        
        # Calcular probabilidades acumulativas para roulette wheel
        for i in range(1, len(self.probas)):
            self.probas[i] += self.probas[i-1]

    def select(self, beta: float) -> int:
        """Selección por roulette wheel para onlooker bees"""
        for index in range(self.size):
            if beta < self.probas[index]:
                return index
        return self.size - 1  # Fallback

    def _check(self, vector: List[float], dim: Optional[int] = None) -> List[float]:
        """Verifica que la solución esté dentro de los bounds"""
        range_ = range(self.dim) if dim is None else [dim]
        
        for i in range_:
            if vector[i] < self.lower[i]:
                vector[i] = self.lower[i]
            elif vector[i] > self.upper[i]:
                vector[i] = self.upper[i]
        
        return vector

    def _verbose(self, itr: int, cost: Dict[str, List[float]]):
        """Imprime información de progreso"""
        print(f"# Iter = {itr} | Best = {cost['best'][itr]:.6f} | Mean = {cost['mean'][itr]:.6f}")

    def get_best_solution(self) -> tuple:
        """Retorna la mejor solución encontrada"""
        return self.solution, self.best 