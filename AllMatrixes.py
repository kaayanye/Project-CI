from typing import TypeVar
from typing import Generic, Union
from vi.config import Config, dataclass, deserialize, serialize
from vi import Matrix

MatrixFloat = TypeVar("MatrixFloat", float, list[float])
MatrixInt = TypeVar("MatrixInt", int, list[int])
    
@dataclass
class AllSchema(Generic[MatrixFloat, MatrixInt]):

        # Parameters of the foxes.
        fox_energy:                 Union[int, MatrixInt] = 8 * 60        # When this runs out the fox dies. Eat to get more energy.
        fox_hunger_threshold:       Union[int, MatrixInt] = 6  * 60       # When energy below this, Fox is hungry and looks for food.
        rabbit_nutrition:           Union[int, MatrixInt] = 30 * 60       # Eating 1 rabbit gives this much energy
        fox_lifespan:               Union[int, MatrixInt] = 3  * 60 * 60  # Foxes die from old age at 3 minutes
        hunt_movespeed:             Union[float, MatrixFloat] = 1.5       # movement speed of fox when tracking scent or chasing rabbit
        track_movespeed:            Union[float, MatrixFloat] = 2
        fox_p_reproduce:            Union[float, MatrixFloat] = 0.3       # Probability of reproduction (create new fox)

        # Parameters of the rabbits.
        rabbit_energy:              Union[int, MatrixInt] = 15 * 60       # When this runs out the rabbit dies. Eat to get more energy.
        rabbit_hunger_threshold:    Union[int, MatrixInt] = 8  * 60       # When energy below this, Rabbit is hungry and looks for food.
        grass_nutrition:            Union[int, MatrixInt] = 5  * 60       # Eating 1 grass gives this much energy
        rabbit_lifespan:            Union[int, MatrixInt] = 3  * 60 * 60  # Rabbits die from old age at 3 minutes
        rabbit_p_reproduce:         Union[float, MatrixFloat] = 0.3       # Probability of reproduction

        # Parameters of the grass.
        grass_t_reproduce:          Union[int, MatrixInt] = 4  * 60       # Delay between reproductions

        # Parameters of the scent.
        scent:                      Union[int, MatrixInt] = 2  * 60       
        scent_interval:             Union[int, MatrixInt] = 30            

        max_fox: int    = Union[int, MatrixInt]
        max_rabbit: int = Union[int, MatrixInt]

@deserialize
@serialize
@dataclass
class AllConfig(Config, AllSchema[list[float], list[int]]):
        
        # Parameters of the foxes.
        fox_energy:                 int = 8 * 60       # When this runs out the fox dies. Eat to get more energy.
        fox_hunger_threshold:       int = 6  * 60       # When energy below this, Fox is hungry and looks for food.
        rabbit_nutrition:           int = 30 * 60       # Eating 1 rabbit gives this much energy
        fox_lifespan:               int = 3  * 60 * 60  # Foxes die from old age at 3 minutes
        hunt_movespeed:             float = 1.5           # movement speed of fox when tracking scent or chasing rabbit
        track_movespeed:            float = 1.5         
        fox_p_reproduce:            float = 0.3         # Probability of reproduction (create new fox)

        # Parameters of the rabbits.
        rabbit_energy:              int = 15 * 60       # When this runs out the rabbit dies. Eat to get more energy.
        rabbit_hunger_threshold:    int = 8  * 60       # When energy below this, Rabbit is hungry and looks for food.
        grass_nutrition:            int = 5  * 60       # Eating 1 grass gives this much energy
        rabbit_lifespan:            int = 3  * 60 * 60  # Rabbits die from old age at 3 minutes
        rabbit_p_reproduce:         float = 0.3         # Probability of reproduction

        # Parameters of the grass.
        grass_t_reproduce:          int = 4  * 60       # Delay between reproductions

        # Parameters of the scent.
        scent:                      Union[int, MatrixInt] = 2  * 60     # COMMENT OUT IF USING BASE_MODEL
        scent_interval:             Union[int, MatrixInt] = 30          # COMMENT OUT IF USING BASE_MODEL

        max_fox: int    = 100
        max_rabbit: int = 100

@dataclass
class AllMatrix(Matrix, AllSchema[list[float], list[int]]):
        radius=[25, 50],
        seed=[1, 2],
        movement_speed=[1],
        duration=[20*60],

        fox_energy              = [8 * 60],
        fox_hunger_threshold    = [6  * 60],
        rabbit_nutrition        = [30 * 60],
        fox_lifespan            = [3  * 60 * 60],
        hunt_movespeed          = [2],
        track_movespeed         = [3],
        fox_p_reproduce         = [0.3],

        rabbit_energy           = [12 * 60],
        rabbit_hunger_threshold = [6  * 60],
        grass_nutrition         = [5  * 60],
        rabbit_lifespan         = [3  * 60 * 60],
        rabbit_p_reproduce      = [0.3],

        grass_t_reproduce       = [4  * 60],

        scent                   = [2  * 60],
        scent_interval          = [30],

        max_fox                 = [500],
        max_rabbit              = [500]