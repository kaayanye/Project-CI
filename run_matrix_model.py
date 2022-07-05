import run_base_model_15
import run_scent_model_15
import AllMatrixes
from multiprocessing import Pool
import seaborn as sn
import os
import polars as pl
import matplotlib.pyplot as plt

def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

if __name__ == "__main__":
    # We create a threadpool to run our simulations in parallel
    with Pool(processes=5, maxtasksperchild=1) as p:
        # The matrix will create unique configs

        # run twice: once with rabbit_nutrition=[30*60, 10*60], rabbit_hunger_threshold=[10*60, 6*60], rabbit_p_reproduce=[0.2, 0.3]

        matrix = AllMatrixes.AllMatrix(
                        radius=[50],
                        seed=[1,2,3,4,5],
                        movement_speed=[1],
                        duration=[8*60*60],

                        fox_energy              = [10800],
                        fox_hunger_threshold    = [600],
                        rabbit_nutrition        = [1800],
                        fox_lifespan            = [10800],
                        hunt_movespeed          = [1.1],
                        track_movespeed         = [1.1],     # COMMENT OUT IF USING BASE_MODEL
                        fox_p_reproduce         = [0.1],

                        rabbit_energy           = [10800],
                        rabbit_hunger_threshold = [600],
                        grass_nutrition         = [300],
                        rabbit_lifespan         = [10800],
                        rabbit_p_reproduce      = [0.1],

                        grass_t_reproduce       = [180],

                        scent                   = [120],     # COMMENT OUT IF USING BASE_MODEL
                        scent_interval          = [30],      # COMMENT OUT IF USING BASE_MODEL

                                                   )
        # Create unique combinations of matrix values
        configs = matrix.to_configs(AllMatrixes.AllConfig)
        print()
        print("Number of configurations: ", len(configs))
        print()
        # print("Number of batches: ", ((len(configs)-(len(configs)%10))/10))
        # print()
        batch_count = 0
        # for conf_batch in batch(configs, 10):
        #     # Create a list of dataframes from each configuration
        #     df_list = p.map(run_base_model_15.run_simulation, conf_batch)
        
        df_list = p.map(run_scent_model_15.run_simulation, configs)
        # Iterate list of dataframes and create plots
        for i, df in enumerate(df_list):

            # Create plot
            foxes = df[df['agent'] == 'fox']
            foxes_count = foxes.groupby('frame', maintain_order=True).agg([pl.col('agent').count()])

            rabbits = df[df['agent'] == 'rabbit']
            rabbits_count = rabbits.groupby('frame', maintain_order=True).agg([pl.col('agent').count()])

            grass = df[df['agent'] == 'grass']
            grass_count = grass.groupby('frame', maintain_order=True).agg([pl.col('agent').count()])

            myPath = os.getcwd()
            fig = plt.figure()
            sn.lineplot(x=rabbits_count['frame'], y=rabbits_count['agent'], palette="tab10", legend='brief', label='Rabbits', linewidth=2)
            sn.lineplot(x=foxes_count['frame'], y=foxes_count['agent'], palette="tab10", legend='brief', label='Foxes', linewidth=2)
            sn.lineplot(x=grass_count['frame'], y=grass_count['agent'], palette="tab10", legend='brief', label='Grass', linewidth=2)

            # Save plot to file
            fig.savefig(myPath+'/scent_plot_'+str(batch_count)+str(i)+'.jpg')

            # Close figure to save memory
            plt.close(fig)

            # Write configuration of the plot to a .txt file
            with open('scent_config_'+str(batch_count)+str(i)+'.txt', 'w') as f:
                f.write(str(configs[i]).replace(',','\n'))
                f.close()
        
        print('Done: Batch '+str(batch_count))
        batch_count += 1

        print('Done!')

