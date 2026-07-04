"""
Artificial Bee Colony (ABC) Algorithm - Original Implementation
=============================================================

Implementación del algoritmo ABC original propuesto por Karaboga (2005).

Paper: "An idea based on honey bee swarm for numerical optimization"

CARACTERÍSTICAS:
- Employed bees: Explotan soluciones conocidas mediante mutación local
- Onlooker bees: Siguen a employed bees exitosos con probabilidad proporcional
- Scout bees: Realizan búsqueda aleatoria cuando se estancan
"""

import random
import copy
import sys
import numpy as np
from typing import Optional, Dict, List, Callable

class Bee:
    """
    Clase individual Bee que representa una solución candidata
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

class ABC_BeeHive:
    """
    Artificial Bee Colony Algorithm (Karaboga, 2005)
    ===============================================
    
    Algoritmo inspirado en el comportamiento de forrajeo de las abejas.
    Tres tipos de abejas:
    - Employed bees: Explotan fuentes de comida conocidas
    - Onlooker bees: Observan y siguen a las employed bees exitosas
    - Scout bees: Buscan nuevas fuentes de comida aleatoriamente
    """
    
    def __init__(self, 
                 lower: List[float], 
                 upper: List[float],
                 fun: Optional[Callable] = None,
                 numb_bees: int = 50,
                 max_itrs: int = 200,
                 max_trials: Optional[int] = None,
                 seed: Optional[int] = 42,
                 verbose: bool = False):
        
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
        
        # Configuración del problema
        self.evaluate = fun
        self.lower = lower
        self.upper = upper
        self.best = sys.float_info.max
        self.solution = None
        
        # Inicializar población
        self.population = [Bee(lower, upper, fun, rng=self.rng) for _ in range(self.size)]
        self.find_best()
        self.compute_probability()

    def run(self) -> Dict[str, List[float]]:
        """
        Ejecuta el algoritmo ABC completo
        """
        cost = {"best": [], "mean": []}
        
        for itr in range(self.max_itrs):
            # Fase 1: Employed Bees
            for index in range(self.size):
                self.send_employee(index)
            
            # Fase 2: Onlooker Bees  
            self.send_onlookers()
            
            # Fase 3: Scout Bees
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
        EMPLOYED BEES PHASE (ABC Original)
        
        Las employed bees modifican UNA dimensión aleatoria usando la ecuación:
        v_ij = x_ij + φ_ij * (x_ij - x_kj)
        
        Donde:
        - v_ij = nueva solución candidata en dimensión j
        - x_ij = solución actual en dimensión j  
        - x_kj = solución vecina aleatoria en dimensión j
        - φ_ij = número aleatorio [-1, 1]
        """
        zombee = copy.deepcopy(self.population[index])
        
        # Seleccionar UNA dimensión aleatoria (clave del ABC original)
        d = self.rng.randint(0, self.dim - 1)
        
        # Seleccionar otra abeja aleatoria
        bee_ix = index
        while bee_ix == index:
            bee_ix = self.rng.randint(0, self.size - 1)
        
        # MUTACIÓN ABC ORIGINAL: solo una dimensión
        zombee.vector[d] = self._mutate(d, index, bee_ix)
        
        # Verificar bounds solo para la dimensión modificada
        zombee.vector = self._check(zombee.vector, dim=d)
        
        # Evaluar nueva solución
        zombee.value = self.evaluate(zombee.vector)
        zombee._fitness()
        
        # Greedy selection
        if zombee.fitness > self.population[index].fitness:
            self.population[index] = copy.deepcopy(zombee)
            self.population[index].counter = 0
        else:
            self.population[index].counter += 1

    def _mutate(self, dim: int, current_bee: int, other_bee: int) -> float:
        """
        Ecuación de mutación ABC original:
        v_ij = x_ij + φ_ij * (x_ij - x_kj)
        """
        phi = (self.rng.random() - 0.5) * 2  # φ ∈ [-1, 1]
        
        return (self.population[current_bee].vector[dim] + 
                phi * (self.population[current_bee].vector[dim] - 
                       self.population[other_bee].vector[dim]))

    def send_onlookers(self):
        """
        ONLOOKER BEES PHASE
        
        Las onlooker bees siguen a employed bees con probabilidad 
        proporcional a su fitness (roulette wheel selection)
        """
        numb_onlookers = 0
        beta = 0
        
        while numb_onlookers < self.size:
            phi = self.rng.random()
            beta += phi * max(self.probas)
            beta %= max(self.probas)
            index = self.select(beta)
            self.send_employee(index)  # Misma operación que employed bees
            numb_onlookers += 1

    def send_scout(self):
        """
        SCOUT BEES PHASE
        
        Si una abeja no mejora por max_trials iteraciones,
        se convierte en scout y busca una nueva solución aleatoria
        """
        trials = [self.population[i].counter for i in range(self.size)]
        index = trials.index(max(trials))
        
        if trials[index] > self.max_trials:
            # Reemplazar con solución completamente aleatoria
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
        """
        Calcula probabilidades de selección para onlooker bees
        basadas en fitness (roulette wheel)
        """
        fitness_sum = sum(bee.fitness for bee in self.population)
        self.probas = [bee.fitness / fitness_sum for bee in self.population]
        
        # Calcular probabilidades acumulativas
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