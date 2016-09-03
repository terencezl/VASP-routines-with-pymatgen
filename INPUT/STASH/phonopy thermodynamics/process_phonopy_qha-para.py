import os
from subprocess import call
import glob
import numpy as np
import run_module as rmd


if __name__ == '__main__':
    """

    Use phonopy to analyze each displacement run of each volume run.

    Not a VASP run script that requires a job submission. You can directly use
    it as

        INPUT/process_phonopy_qha.py INPUT/run_phonopy_qha.yaml

    to read a specs file at INPUT/run_phonopy_qha.yaml, which is the file you
    would use to actually run the routine script run_phonopy_qha-para.py before
    this.

    You should set a 'phonopy' tag in the specs file in the format documented in
    the script run_phonopy_qha-para.py.

    Optionally, you can set a tag 'qha_only' to be True to skip the per volume
    phonopy evaluation, and just run phonopy_qha,

        phonopy:
          qha_only: True

    """

    run_specs, filename = rmd.get_run_specs_and_filename()
    rmd.chdir(rmd.get_run_dir(run_specs))
    phonopy_specs = run_specs['phonopy']
    phonopy_specs['dim'] = ' '.join(map(str, phonopy_specs['dim']))
    phonopy_specs['mp'] = ' '.join(map(str, phonopy_specs['mp']))
    phonopy_specs['tmax'] = str(phonopy_specs['tmax'])
    phonopy_specs['tstep'] = str(phonopy_specs['tstep'])

    run_volume_dirname = phonopy_specs['volumes_and_structures']['from']\
        if 'volumes_and_structures' in phonopy_specs and \
           'from' in phonopy_specs['volumes_and_structures'] and \
           phonopy_specs['volumes_and_structures']['from'] else 'run_volume'

    if isinstance(run_volume_dirname, str):
        fitting_results = rmd.fileload(os.path.join('..',
            run_volume_dirname, 'fitting_results.json'))[-1]
        volume = fitting_results['volume']
        energy = fitting_results['energy']
    elif isinstance(run_volume_dirname, list):
        volume = []
        energy = []
        for dirname in run_volume_dirname:
            fitting_results = rmd.fileload(os.path.join('..',
                dirname, 'fitting_results.json'))[-1]
            volume.extend(fitting_results['volume'])
            energy.extend(fitting_results['energy'])

    idx_slice = phonopy_specs['volumes_and_structures']['slice'] if \
        'volumes_and_structures' in phonopy_specs and \
        'slice' in phonopy_specs['volumes_and_structures'] and \
        phonopy_specs['volumes_and_structures']['slice'] else [None] * 2

    volume, energy = np.array(sorted(zip(volume, energy)))[idx_slice[0]:idx_slice[1]].T

    if not ('qha_only' in phonopy_specs and phonopy_specs['qha_only']):
        for V in volume:
            rmd.chdir(str(np.round(V, 2)))
            if phonopy_specs['mode'] == 'force_set':
                disp_dirs = sorted(glob.glob('disp-*'))
                disp_vasprun_xml = ' '.join([i + '/vasprun.xml' for i in disp_dirs])
                call('phonopy -f ' + disp_vasprun_xml + ' > /dev/null', shell=True)
                call('phonopy --mp="' + phonopy_specs['mp'] + '" -tsp --dim="' + phonopy_specs['dim'] +
                    '" --tmax=' + phonopy_specs['tmax'] + ' --tstep=' + phonopy_specs['tstep'] +
                    ' > /dev/null', shell=True)
            elif phonopy_specs['mode'] == 'force_constant':
                call('phonopy --fc vasprun.xml > /dev/null 2>&1', shell=True)
                call('phonopy --readfc -c POSCAR_orig --mp="' + phonopy_specs['mp'] +
                    '" -tsp --dim="' + phonopy_specs['dim'] + '" --tmax=' + phonopy_specs['tmax'] +
                    ' --tstep=' + phonopy_specs['tstep'] + ' > /dev/null 2>&1', shell=True)
            os.chdir('..')

    # post processing
    e_v_dat = np.column_stack((volume, energy))
    np.savetxt('../e-v.dat', e_v_dat, '%15.6f', header='volume energy')
    thermal_properties = ' '.join([str(i) + '/thermal_properties.yaml' for i in np.round(volume, 2)])
    call('phonopy-qha ../e-v.dat ' + thermal_properties +
        ' -s --tmax=' + phonopy_specs['tmax'] + ' > /dev/null', shell=True)
