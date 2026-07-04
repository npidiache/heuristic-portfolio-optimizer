"""
ABC-Scout-Gravitacional Algorithm
================================

Implementación del algoritmo híbrido ABC con fase de exploradora basada en
búsqueda gravitacional, utilizando herencia para una estructura de código limpia.

INNOVACIÓN CLAVE:
- La clase `ABC_Scout_Gravitacional` hereda toda la funcionalidad de `ABC_BeeHive`.
- Se sobrescribe únicamente el método `send_scout` para implementar la
  búsqueda gravitacional basada en la Ley de Gravitación Universal de Newton.
"""

import math
import random
import numpy as np
from typing import List, Tuple
from .abc_original import ABC_BeeHive, Bee

class ABC_Scout_Gravitacional(ABC_BeeHive):
    """
    ABC con fase de exploradora basada en búsqueda gravitacional.
    
    INNOVACIÓN: La abeja exploradora calcula la fuerza gravitacional neta
    ejercida por todo el enjambre y se mueve en esa dirección, en lugar
    de realizar búsqueda aleatoria o seguir un solo objetivo.
    """
    
    def __init__(self, *args, **kwargs):
        # Extraer parámetros específicos del Scout-Gravitacional
        self.G = kwargs.pop('G', 1.0)  # Constante gravitacional
        self.epsilon = kwargs.pop('epsilon', 1e-10)  # Pequeño valor para evitar división por cero
        self.alpha = kwargs.pop('alpha', 0.1)  # Factor de aleatorización
        
        # Llamar al constructor de la clase padre (ABC_BeeHive)
        super().__init__(*args, **kwargs)

    def _calculate_gravitational_force(self, scout_bee: Bee, target_bee: Bee) -> List[float]:
        """
        Calcula la fuerza gravitacional entre dos abejas.
        
        F = G * (m1 * m2) / (r² + ε)
        donde:
        - m1, m2 son las "masas" (fitness) de las abejas
        - r es la distancia euclidiana entre sus posiciones
        - G es la constante gravitacional
        - ε es un pequeño valor para evitar división por cero
        
        Args:
            scout_bee: Abeja exploradora (receptor de la fuerza)
            target_bee: Abeja objetivo (ejerce la fuerza)
            
        Returns:
            List[float]: Vector de fuerza en cada dimensión
        """
        # Calcular distancia euclidiana
        distance = math.sqrt(sum((s_v - t_v) ** 2 for s_v, t_v in 
                                zip(scout_bee.vector, target_bee.vector)))
        
        # Evitar división por cero
        if distance < self.epsilon:
            return [0.0] * self.dim
        
        # Calcular "masas" basadas en fitness
        # Nota: fitness ya está normalizado en [0,1] en la clase Bee
        mass_scout = scout_bee.fitness
        mass_target = target_bee.fitness
        
        # Calcular magnitud de la fuerza gravitacional
        force_magnitude = self.G * (mass_scout * mass_target) / (distance ** 2 + self.epsilon)
        
        # Calcular vector de dirección unitario
        direction_vector = []
        for d in range(self.dim):
            direction = (target_bee.vector[d] - scout_bee.vector[d]) / distance
            direction_vector.append(direction)
        
        # Retornar vector de fuerza en cada dimensión
        force_vector = [force_magnitude * direction_vector[d] for d in range(self.dim)]
        
        return force_vector

    def _calculate_net_gravitational_force(self, scout_bee: Bee) -> List[float]:
        """
        Calcula la fuerza gravitacional neta ejercida por todo el enjambre
        sobre la abeja exploradora.
        
        Args:
            scout_bee: Abeja exploradora que recibe la fuerza neta
            
        Returns:
            List[float]: Vector de fuerza neta en cada dimensión
        """
        net_force = [0.0] * self.dim
        
        for target_bee in self.population:
            # No calcular fuerza consigo misma
            if target_bee is scout_bee:
                continue
                
            # Calcular fuerza individual
            individual_force = self._calculate_gravitational_force(scout_bee, target_bee)
            
            # Sumar a la fuerza neta
            for d in range(self.dim):
                net_force[d] += individual_force[d]
        
        return net_force

    def send_scout(self):
        """
        FASE MODIFICADA: Abeja exploradora guiada por búsqueda gravitacional.
        
        Esta función sobrescribe el `send_scout` de la clase `ABC_BeeHive`.
        
        INNOVACIÓN:
        1. Identifica la abeja estancada (scout)
        2. Calcula la fuerza gravitacional neta ejercida por todo el enjambre
        3. Mueve la scout en la dirección de la fuerza neta
        4. Añade componente aleatorio para mantener diversidad
        """
        trials = [bee.counter for bee in self.population]
        
        # Encontrar el índice de la abeja con el máximo número de intentos
        try:
            index = trials.index(max(trials))
        except ValueError:
            return  # No hay nada que hacer si la lista está vacía

        if trials[index] > self.max_trials:
            # --- INICIO del Mecanismo Scout-Gravitacional ---
            scout_bee = self.population[index]
            
            # Verificar que el enjambre tenga al menos 2 abejas
            if len(self.population) < 2:
                # Fallback: búsqueda aleatoria si no hay suficientes abejas
                self.population[index] = Bee(self.lower, self.upper, self.evaluate, rng=self.rng)
                self.population[index].counter = 0
                return

            # 1. Calcular fuerza gravitacional neta del enjambre
            net_force = self._calculate_net_gravitational_force(scout_bee)
            
            # 2. Normalizar la fuerza neta para evitar movimientos excesivos
            force_magnitude = math.sqrt(sum(f**2 for f in net_force))
            if force_magnitude > 0:
                normalized_force = [f / force_magnitude for f in net_force]
            else:
                normalized_force = [0.0] * self.dim
            
            # 3. Calcular nueva posición con movimiento gravitacional
            new_vector = [0.0] * self.dim
            for d in range(self.dim):
                current_pos = scout_bee.vector[d]
                
                # Movimiento gravitacional: posición actual + fuerza normalizada
                gravitational_movement = normalized_force[d]
                
                # Componente aleatorio para mantener diversidad
                random_component = self.alpha * (self.rng.random() - 0.5)
                
                # Nueva posición
                new_vector[d] = current_pos + gravitational_movement + random_component
            
            # 4. Actualizar la abeja scout directamente
            scout_bee.vector = self._check(new_vector)
            scout_bee.value = self.evaluate(scout_bee.vector)
            scout_bee._fitness()
            scout_bee.counter = 0
            # --- FIN del Mecanismo Scout-Gravitacional ---

    def get_algorithm_info(self) -> dict:
        """
        Retorna información sobre el algoritmo para análisis y documentación.
        
        Returns:
            dict: Información del algoritmo incluyendo parámetros y fundamento teórico
        """
        return {
            'name': 'ABC-Scout-Gravitacional',
            'description': 'ABC con fase de exploradora basada en búsqueda gravitacional',
            'parameters': {
                'G': self.G,
                'epsilon': self.epsilon,
                'alpha': self.alpha
            },
            'theoretical_basis': {
                'principle': 'Ley de Gravitación Universal de Newton',
                'innovation': 'Uso holístico de información del enjambre vs. seguir un solo líder',
                'robustness': 'Mayor resistencia a óptimos locales por uso de múltiples fuerzas'
            },
            'complexity': {
                'scout_phase': 'O(N²) donde N es el tamaño del enjambre',
                'advantage': 'Exploración más suave y robusta'
            }
        } 