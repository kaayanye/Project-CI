import random
from multiprocessing import Pool
import polars as pl
import pygame as pg
from pygame.sprite import Group
from vi import Agent, HeadlessSimulation, Simulation, util, Window
from vi.config import Config, dataclass, deserialize


#######################################
###          Class Configs          ###
#######################################

@deserialize
@dataclass
class AllConfig(Config):

        # Parameters of the foxes
        fox_energy:                 int = 10800     # When this runs out the fox dies. Eat to get more energy.
        fox_hunger_threshold:       int = 480       # When energy below this, Fox is hungry and looks for food.
        rabbit_nutrition:           int = 600       # Eating 1 rabbit gives this much energy
        fox_lifespan:               int = 10800     # Foxes die from old age at 3 minutes
        hunt_movespeed:             int = 1.1       # movement speed of fox when hunting rabbit
        track_movespeed:            int = 1.5       # movement speed of fox when tracking rabbit
        fox_p_reproduce:            float = 0.2     # Probability of reproduction (create new fox)

        # Parameters of the rabbits
        rabbit_energy:              int = 10800     # When this runs out the rabbit dies. Eat to get more energy.
        rabbit_hunger_threshold:    int = 600       # When energy below this, Rabbit is hungry and looks for food.
        grass_nutrition:            int = 300       # Eating 1 grass gives this much energy
        rabbit_lifespan:            int = 10800     # Rabbits die from old age at 3 minutes
        rabbit_p_reproduce:         float = 0.2     # Probability of reproduction

        # Parameters of the grass
        grass_t_reproduce:          int = 180       # Delay between reproductions

        # Parameters of the scent
        scent:                      int = 120       # When this runs out the scent disappears
        scent_interval:             int = 30        # How often rabbits drop a scent        

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
        self.energy         = self.config.fox_hunger_threshold-1
        self.nutrition      = self.config.rabbit_nutrition
        self.hunger         = self.config.fox_hunger_threshold
        self.lifespan       = int(self.config.fox_lifespan * noise) # lifespans are randomised a bit
        self.p_reproduce    = self.config.fox_p_reproduce
        self.hunt_movespeed = self.config.hunt_movespeed
        self.track_movespeed = self.config.track_movespeed
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
        self.save_data("agent", "fox")
        self.save_data("age", self.age)
        self.save_data("max_lifespan", self.lifespan)
        self.save_data("energy", self.energy)
        self.save_data("reproduce", reproduce)
        self.save_data("eat", self.eat)

    def closestRabbit(self):
        # Get the rabbit closest to the fox

        # Get list of rabbits in proximity
        candidates = (
                self.in_proximity_accuracy()
                .without_distance()
                .filter_kind(Rabbit)
            )
        # Pick first rabbit in list
        closest = candidates.first()
        if closest:
            for i in candidates:
                # Compare distance from fox with all other candidates
                if i.state == 0 and (self.pos - i.pos).length() < (self.pos - closest.pos).length():
                    closest = i
            # Rabbit closest to fox is returned
            return closest if closest.state == 0 else False
        else:
            return False
        
    def oppositeVector(self,first,second):
        # Get opposite vector from the first to the second entity
        return first.pos - second.pos

    def gotoVector(self,first, second):
        # Get vector from the first to the second entity
        return second.pos - first.pos 

    def change_position(self):
        
        self.there_is_no_escape()
        # Check for rabbits nearby
        rabbit_list = (
            self.in_proximity_accuracy()
                .without_distance()
                .filter_kind(Rabbit)
        )

        rabbit = None

        # Getting a list of the nearby scent entities
        scent_list = [i for i in rabbit_list if i.state == 1]

        # Set flags to 0 (used in saving data from simulation)
        self.track = 0 
        self.chase = 0
        self.eat   = 0

        # If there are rabbits in proximity when hungry:
        if self.energy < self.hunger:
            rabbit = self.closestRabbit()
            # Eat rabbit if close
            if rabbit:
                # If a rabbit is close enough, the fox eats it and replenishes energy
                if self.pos.distance_to(rabbit.pos) < 20:
                    rabbit.kill()
                    self.energy += self.nutrition
                    if self.energy > self.config.fox_energy:
                        self.energy = self.config.fox_energy
                    self.eat = 1  # set kill flag
                # Otherwise chase rabbit by following its relative position vector
                else:
                    self.move = self.gotoVector(self,rabbit).normalize() * self.hunt_movespeed
                    self.chase = 1  # set chase flag
            # If there exists nearby scentes, we should chase these scents with a heightened move speed
            elif scent_list != []:
                scentVector = pg.Vector2(0,0)
                for scent in scent_list:
                    # All scents that are too close are ignored to avoid following too closely
                    if self.gotoVector(self,scent).length() > 10:
                        # Aggregation of scent vectors, favoring scents that are further away and stronger
                        scentVector += self.gotoVector(self,scent) * (self.gotoVector(self,scent).length()  ** 3) * (scent.scent ** 4) / 1200
                if scentVector.length() > 0:
                    scentVector = scentVector.normalize()
                # Only adjust the previous movement vector by a fraction of the new movement vector
                # This mechanism is for momentum, creating smoother movement. Due to a typo the eventual
                # momentum factor is in fact 0.83 (1 + 0.7*0.3 = 1.21 which gets normalized so 1 / 1.21 = 0.83)
                self.move = self.move + 0.7 * 0.3*scentVector
                self.track = 1
        # Otherwise: default movement
        else:
            changed = self.there_is_no_escape()

            prng = self.shared.prng_move

            # Always calculate the random angle so a seed could be used.
            deg = prng.uniform(-30, 30)

            # Only update angle if the agent was teleported to a different area of the simulation.
            if changed:
                self.move.rotate_ip(deg)

            # Random opportunity to slightly change angle.
            # Probabilities are pre-computed so a seed could be used.
            should_change_angle = prng.random()
            deg = prng.uniform(-10, 10)

            # Only allow the angle opportunity to take place when no collisions have occured.
            # This is done so an agent always turns 180 degrees. Any small change in the number of degrees
            # allows the agent to possibly escape the obstacle.
            if 0.25 > should_change_angle:
                self.move.rotate_ip(deg)

        # If the movement vector is not null, we can normalise and adjust it by the appropriate movement speed
        # depending on its current state        
        if self.move.length() > 0:
            self.move = self.move.normalize()
        if self.chase == 1: 
            self.move *= self.hunt_movespeed
        elif self.track == 1:
            self.move *= self.track_movespeed

        # Actually update the position at last.
        self.pos += self.move

class Rabbit(Agent):
    config: AllConfig

    def on_spawn(self):

        # Gaussian noise used for some parameters
        noise = abs(random.gauss(1, 0.25))
        # init parameters
        self.energy         = self.config.rabbit_hunger_threshold-1
        self.hunger         = self.config.rabbit_hunger_threshold
        self.nutrition      = self.config.grass_nutrition
        self.lifespan       = int(self.config.rabbit_lifespan * noise)
        self.p_reproduce    = self.config.rabbit_p_reproduce
        self.age            = 0
        self.state = 0  # 0 if rabbit, 1 if scent
        self.scent = self.config.scent
        self.scent_interval = self.config.scent_interval  # How often rabbits drop scent
        self.scent_id = None  # ID of the agent the scent belongs to. None is agent is a rabbit.

    def update(self):

        # If agent is rabbit (not scent)
        if self.state == 0:

            # Update parameters
            self.age     += 1  # Aging process.
            self.energy  -= 1  # Metabolism process (spend energy)
            
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

            # Spawn scent each scent_interval
            if self.age % self.scent_interval == 0:
                scent = self.reproduce()
                scent.state = 1  # use this rabbit as scent
                scent.scent_id = self

            self.save_data("agent", "rabbit")
            self.save_data("age", self.age)
            self.save_data("max_lifespan", self.lifespan)
            self.save_data("energy", self.energy)
            self.save_data("reproduce", reproduce)
            self.save_data("eat", eat)

        # If agent is being used as scent
        elif self.state == 1:

            # If scent timer has run out, kill agent
            if self.scent == 0:
                self.kill()

            if Agent.is_dead(self.scent_id):
                self.kill()
            
            # Use scent image instead of rabbit image
            self.change_image(1)

            # Count down scent timer
            self.scent -= 1

            self.save_data("agent", "scent")
            self.save_data("age", 0)
            self.save_data("max_lifespan", 0)
            self.save_data("energy", 0)
            self.save_data("reproduce", 0)
            self.save_data("eat", 0)

    def change_position(self):

        if self.state == 0:
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

        # If agent is used as scent: Give it no movement ability
        else:
            pass

########################################
###            Simulation            ###
########################################

def run_simulation(config: AllConfig) -> pl.DataFrame:
    df = (
        HeadlessSimulation(config)
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

