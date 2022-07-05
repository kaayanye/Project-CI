import math
import random
from multiprocessing import Pool
import pygame as pg
import polars as pl
from pygame.sprite import Group
from vi import Agent, HeadlessSimulation, Simulation, util, Window
from vi.config import Config, dataclass, deserialize, serialize

#######################################
###          Class Configs          ###
#######################################

@deserialize
@dataclass
class AllConfig(Config):

        # Parameters of the foxes.
        fox_energy:                 int = 10800       # When this runs out the fox dies. Eat to get more energy.
        fox_hunger_threshold:       int = 360       # When energy below this, Fox is hungry and looks for food.
        rabbit_nutrition:           int = 1800       # Eating 1 rabbit gives this much energy
        fox_lifespan:               int = 10800  # Foxes die from old age at 3 minutes
        hunt_movespeed:             int = 1.1           # movement speed of fox when tracking scent or chasing rabbit
        fox_p_reproduce:            float = 0.2         # Probability of reproduction (create new fox)

        # Parameters of the rabbits.
        rabbit_energy:              int = 10800       # When this runs out the rabbit dies. Eat to get more energy.
        rabbit_hunger_threshold:    int = 600       # When energy below this, Rabbit is hungry and looks for food.
        grass_nutrition:            int = 300       # Eating 1 grass gives this much energy
        rabbit_lifespan:            int = 10800  # Rabbits die from old age at 3 minutes
        rabbit_p_reproduce:         float = 0.2         # Probability of reproduction

        # Parameters of the grass.
        grass_t_reproduce:          int = 180        # Time before grass is back for consumption again

        window=Window(750, 750)
 


#######################################
###             Classes             ###
#######################################


class Grass(Agent):
    config: AllConfig

    def on_spawn(self):

        # If first tick of the simulation:
        if self.shared.counter == 0:
            # Grass is given a random position in the simulation
            self.pos = util.random_pos(pg.rect.Rect(1, 1, 749, 749))

        _obstacles: Group
        # init parameters
        self.t_reproduce    = self.config.grass_t_reproduce + int(random.gauss(60, 20)) # Offset initial reproduction timers
        self.state          = 1                                                         # State 1 = Grass is available for consumption State 0 = Grass is not available for consumption
        self.timer          = self.t_reproduce                                          # Timer which is initiated to keep track of time after being eaten
        
        # Freeze movement. Grass does not walk.
        self.freeze_movement()

    def eaten(self):
        self.pos = util.random_pos(pg.rect.Rect(1, 1, 749, 749))                        # Change position randomly
        self.change_image(1)                                                            # Change image to visually indicate unavailable grass
        self.state = 0                                                                  # Set state to 0

    def update(self):

        # set reproduce flag
        reproduce = 0

        if self.state == 0:         
            self.timer -= 1                                                             # If eaten, count down timer per step
            if self.timer == 0:
                self.state = 1                                                          # With timer 0, set state to be alive again
                self.change_image(0)                                                    # Change image to green
                self.timer = self.t_reproduce                                           # Reinitialize timer
                

        if self.state == 1:
            self.save_data("agent", "grass")
        else:
            self.save_data("agent", "dead_grass")

        self.save_data("age", 0)
        self.save_data("max_lifespan", 0)
        self.save_data("energy", 0)
        self.save_data("reproduce", reproduce)
        self.save_data("eat", 0)

class Fox(Agent):
    config: AllConfig

    def on_spawn(self):

        _obstacles: Group

        # Gaussian noise used for some parameters
        noise = abs(random.gauss(1, 0.25))

        # init parameters
        self.energy         = self.config.fox_hunger_threshold
        self.nutrition      = self.config.rabbit_nutrition
        self.hunger         = self.config.fox_hunger_threshold
        self.lifespan       = int(self.config.fox_lifespan * noise) # lifespans are randomised a bit
        self.p_reproduce    = self.config.fox_p_reproduce
        self.hunt_movespeed = self.config.hunt_movespeed
        self.age            = 0

    def update(self):

        # set reproduction flag for saving data
        reproduce = 0

        self.age += 1       # Aging process.
        self.energy -= 1    # Metabolism process (spend energy)

        # Kill agent if too old or out of energy
        if self.age == self.lifespan or self.energy == 0:
            self.kill()

        # Check for other foxes nearby
        fox = (
             self.in_proximity_accuracy()
             .without_distance()
             .filter_kind(Fox)
             .first()
         )
        
        if self.energy > self.hunger and fox is not None:
                if util.probability(self.p_reproduce):
                    self.reproduce()
                    fox.energy = self.config.fox_hunger_threshold-1
                    self.energy = self.config.fox_hunger_threshold-1
                    reproduce = 1

        # Save data to the dataframe
        self.save_data("agent", 'fox')
        self.save_data("age", self.age)
        self.save_data("max_lifespan", self.lifespan)
        self.save_data("energy", self.energy)
        self.save_data("reproduce", reproduce)
        self.save_data("eat", self.eat)

    def change_position(self):
        
        # Check for rabbits nearby
        rabbit = (
             self.in_proximity_accuracy()
             .without_distance()
             .filter_kind(Rabbit)
             .first()
         )

        # Set flags to 0 (used in saving data from simulation)
        self.track, self.chase, self.eat = 0, 0, 0

        # If there are rabbits in proximity when hungry:
        if self.energy < self.hunger and rabbit is not None:
            # Eat rabbit if close
            if self.pos.distance_to(rabbit.pos) < 20:
                rabbit.kill()
                self.energy += self.nutrition
                if self.energy > self.config.fox_energy:
                    self.energy = self.config.fox_energy
                self.eat = 1 # set kill flag

            # Otherwise chase rabbit
            else:
                angle = self.pos.angle_to(rabbit.pos)           # Angle between rabbit and fox
                self.move = pg.Vector2(self.hunt_movespeed, 0)  # movement vector with hunt_movespeed
                self.move.rotate_ip(angle)                      # rotate movement vector towards rabbit
                self.chase = 1                                  # set chase flag

        # Otherwise: default movement
        else:
            changed = self.there_is_no_escape()

            prng = self.shared.prng_move

            # Always calculate the random angle so a seed could be used.
            deg = prng.uniform(-30, 30)

            # Only update angle if the agent was teleported to a different area of the simulation.
            if changed:
                self.move.rotate_ip(deg)

            # Obstacle Avoidance
            obstacle_hit = pg.sprite.spritecollideany(self, self._obstacles, pg.sprite.collide_mask)  # type: ignore
            collision = bool(obstacle_hit)

            # Reverse direction when colliding with an obstacle.
            if collision and not self._still_stuck:
                self.move.rotate_ip(180)
                self._still_stuck = True

            if not collision:
                self._still_stuck = False

            # Random opportunity to slightly change angle.
            # Probabilities are pre-computed so a seed could be used.
            should_change_angle = prng.random()
            deg = prng.uniform(-10, 10)

            # Only allow the angle opportunity to take place when no collisions have occured.
            # This is done so an agent always turns 180 degrees. Any small change in the number of degrees
            # allows the agent to possibly escape the obstacle.
            if not collision and not self._still_stuck and 0.25 > should_change_angle:
                self.move.rotate_ip(deg)
            
            self.move.normalize()

        # Actually update the position at last.
        self.pos += self.move

class Rabbit(Agent):
    config: AllConfig

    def on_spawn(self):

        # Gaussian noise used for some parameters
        noise = abs(random.gauss(1, 0.25))
        # init parameters
        self.energy         = self.config.rabbit_hunger_threshold
        self.hunger         = self.config.rabbit_hunger_threshold
        self.nutrition      = self.config.grass_nutrition
        self.lifespan       = int(self.config.rabbit_lifespan * noise)
        self.p_reproduce    = self.config.rabbit_p_reproduce
        self.age            = 0

    def update(self):

        # Update parameters
        self.age            += 1        # Aging process.
        self.energy         -= 1        # Metabolism process (spend energy)
        
        # Set flags for data collection
        eat, reproduce = 0, 0

        # Kill agent if too old or out of energy
        if self.age == self.lifespan or self.energy == 0:
            self.kill()

        # Check for grass nearby
        grass = (
            self.in_proximity_accuracy()
            .without_distance()
            .filter_kind(Grass)
            .filter(lambda agent: agent.state == 1)     #Filter only the grass that is alive
            .first()
        )

        # Check for other rabbits nearby
        rabbit = (
            self.in_proximity_accuracy()
            .without_distance()
            .filter_kind(Rabbit)
            .first()
        )

        # If hungry and grass is nearby then eat grass
        if self.energy < self.hunger and grass is not None and grass.state == 1:
            grass.eaten()
            self.energy += self.nutrition
            if self.energy > self.config.rabbit_energy:
                self.energy = self.config.rabbit_energy
            eat = 1
        
        # If not hungry and other rabbits are nearby then attempt reproduction
        elif self.energy > self.hunger and rabbit is not None:
                if util.probability(self.p_reproduce):
                    self.reproduce()
                    rabbit.energy = self.config.rabbit_hunger_threshold-1
                    self.energy = self.config.rabbit_hunger_threshold-1
                    reproduce = 1

        self.save_data("agent", 'rabbit')
        self.save_data("age", self.age)
        self.save_data("max_lifespan", self.lifespan)
        self.save_data("energy", self.energy)
        self.save_data("reproduce", reproduce)
        self.save_data("eat", eat)

class FoxRabbitHeadless(HeadlessSimulation):
    config: AllConfig
    def after_update(self):
        ...


########################################
###            Simulation            ###
########################################

def run_simulation(config: AllConfig) -> pl.DataFrame:
    df = (
        FoxRabbitHeadless(config)
        .batch_spawn_agents(20, Fox, images=["images/fox.png"])
        .batch_spawn_agents(20, Rabbit, images=["images/rabbit.png", "images/white.png"])
        .batch_spawn_agents(60, Grass, images=["images/green.png", "images/red.png"])
        .run()
        .snapshots
    )
    print()
    print("Finished! Simulation ID "+str(config.id))
    print()
    return df