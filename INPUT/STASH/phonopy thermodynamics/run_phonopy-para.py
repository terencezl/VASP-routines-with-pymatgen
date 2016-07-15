import os
import shutil
from subprocess import call
import glob
import run_module as rmd
import pymatgen as mg


if __name__ == '__main__':
    """

    Run the phonopy force set calculation for a constant volume.

    You should set a 'phonopy' tag in the specs file like

        phonopy:
          mode: force_set (or force_constant)
          dim: [2, 2, 2]
          mp: [31, 31, 31]
          tmax: 1400
          tstep: 5

    """

    run_specs, filename = rmd.get_run_specs_and_filename()
    cwd = os.getcwd()
    rmd.chdir(rmd.get_run_dir(run_specs))
    rmd.filedump(run_specs, filename)

    phonopy_dim = ' '.join(map(str, run_specs['phonopy']['dim']))
    phonopy_mp = ' '.join(map(str, run_specs['phonopy']['mp']))
    phonopy_tmax = str(run_specs['phonopy']['tmax'])
    phonopy_tstep = str(run_specs['phonopy']['tstep'])

    rmd.infer_from_json(run_specs)
    structure = rmd.get_structure(run_specs)
    incar = rmd.read_incar(run_specs)
    kpoints = rmd.read_kpoints(run_specs, structure)

    if run_specs['phonopy']['mode'] == 'force_set':
        structure.to(filename='POSCAR')
        call('phonopy -d --dim="' + phonopy_dim + '" > /dev/null', shell=True)
        os.remove('SPOSCAR')
        disp_structures = sorted(glob.glob('POSCAR-*'))
        disp_dirs = ['disp-' + i.split('POSCAR-')[1] for i in disp_structures]
        for disp_d, disp_p in zip(disp_dirs, disp_structures):
            rmd.chdir(disp_d)
            rmd.init_stdout()
            shutil.move('../' + disp_p, 'POSCAR')
            incar.write_file('INCAR')
            kpoints.write_file('KPOINTS')
            rmd.write_potcar(run_specs)
            job = disp_d
            shutil.copy(cwd + '/INPUT/deploy.job', job)
            call('sed -i "/python/c time ' + rmd.VASP_EXEC + ' 2>&1 | tee -a stdout" ' + job, shell=True)
            call('M ' + job, shell=True)
            os.remove(job)
            os.chdir('..')
    elif run_specs['phonopy']['mode'] == 'force_constant':
        rmd.init_stdout()
        incar.write_file('INCAR')
        kpoints.write_file('KPOINTS')
        structure.to(filename='POSCAR')
        call('phonopy -d --dim="' + phonopy_dim + '" > /dev/null', shell=True)
        os.rename('POSCAR', 'POSCAR_orig')
        os.rename('SPOSCAR', 'POSCAR')
        os.remove('disp.yaml')
        for f in glob.glob('POSCAR-*'):
            os.remove(f)
        rmd.write_potcar(run_specs)
        job = 'run_phonopy_fc'
        shutil.copy(cwd + '/INPUT/deploy.job', job)
        call('sed -i "/python/c time ' + rmd.VASP_EXEC + ' 2>&1 | tee -a stdout" ' + job, shell=True)
        call('M ' + job, shell=True)
        os.remove(job)
