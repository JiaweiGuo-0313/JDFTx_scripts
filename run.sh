#!/bin/bash
#SBATCH --exclude=agate-0,agate-1,agate-10,agate-16,agate-19,agate-26,agate-28,agate-29,agate-40,agate-43
#SBATCH --nodes=1 --partition=high
#SBATCH --ntasks-per-node=16
#SBATCH --ntasks-per-core=4
#SBATCH --threads-per-core=1
#SBATCH --error=job.err
#SBATCH --output=job.out
#SBATCH --time=38:00:00
#SBATCH --verbose

module load jdftx/1.7.0

export SLURM_CPU_BIND="cores"
export JDFTX_MEMPOOL_SIZE=8192

nIter='10'
charge='0'  # measured in electrons. eg. OH- will have charge +1,  H3O+ will have charge -1

# starting from existing .xyz, geometry optimization without solvation (in vacuum)
start_name='start'
job_name='Vacuum'
solvent=''

# setups geometry optimization now including solvation
# start_name='Vacuum'
# job_name='CANDLE'
# solvent='CH3CN'

# run geometry optimization until convergence is reached
python setup_jdftx.py NEW $job_name $start_name $nIter $charge $solvent
srun -n 1 -c 16 jdftx -i $job_name.in -o $job_name.out -d  # overwrite

for i in {1..20}
do
job_status=$(python setup_jdftx.py RERUN $job_name $start_name $nIter $charge $solvent)

if [ "$job_status" != "converged" ];
then
echo $i
srun -n 1 -c 16 jdftx -i $job_name.in -o $job_name.out;  # append mode
fi;

done

