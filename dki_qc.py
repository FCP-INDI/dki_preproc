import nipype.pipeline.engine as pe
from nipype.interfaces import slicer
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import os,glob,sys

def create_diff_qc(name='diff_qc'):

    diff_qc=pe.Workflow(name=name)

    inputspec = pe.Node(util.IdentityInterface(fields=['diff',
                                                       'bvals',
                                                       'bvecs']),
                        name='inputspec')

    outputspec = pe.Node(util.IdentityInterface(fields=['diffnrrd',
                                                        'outputFolder',
                                                        'faMap']),
                         name='outputspec')


    nii2nrrd = pe.Node(interface=slicer.DWIConvert(), name='nii2nrrd')
    nii2nrrd.inputs.conversionMode='FSLToNrrd'
    nii2nrrd.inputs.outputVolume='dwi.nrrd'

    dwiqc = pe.Node(interface=slicer.DTIPrep(), name='dwiqc')
    dwiqc.inputs.xmlProtocol = '/home/davidoconner/dki_preproc/QC/tutorialProtocol.xml'
    dwiqc.inputs.check = True
    dwiqc.inputs.outputFolder = 'dwiqc/'
    #dwiqc.inputs.faMap = 'test'
    dwiqc.inputs.numberOfThreads = 4


    #nrrd2nii  = pe.Node(interface=slicer.DWIConvert(), name='nrrd2nii')
    #nii2nrrd.inputs.conversionMode='NrrdToFSL'
    #nii2nrrd.inputs.outputNiftiFile='fa.nii'

    diff_qc.connect([

    (inputspec, nii2nrrd, [('bvals', 'inputBValues')]),
    (inputspec, nii2nrrd, [('bvecs', 'inputBVectors')]),
    (inputspec, nii2nrrd, [('diff', 'inputVolume')]),
    (nii2nrrd, outputspec, [('outputVolume','diffnrrd')]),
    (nii2nrrd, dwiqc, [('outputVolume','DWINrrdFile')]),
    (dwiqc, outputspec, [('outputFolder','outputFolder')]),
    (dwiqc, outputspec, [('faMap','faMap')])
    ])
    
    return diff_qc


if __name__ == '__main__':

    ## Intialize variables and workflow
    globaldir='/home/davidoconner/dki_preproc/qcwflow/'
    workdir='/home/davidoconner/dki_preproc/qcwflow/working/'
    qc = pe.Workflow(name='qcwflow')
    qc.base_dir = workdir

    ipdir='/home/davidoconner/raw_data/hbnssi/'
    sublist=[g.split('/')[-2] for g in glob.glob(ipdir+'*/')]
    seslist=['ses-SSV1']
    #seslist=list(set([g.split('/')[-2] for g in glob.glob(ipdir+'*/*/')]))


    ## Setup data managment nodes

    infosource = pe.Node(util.IdentityInterface(fields=['subject_id','session_id']),name="infosource")
    infosource.iterables = [('subject_id', sublist),('session_id', seslist)]

    templates={
    'dki' : ipdir+'{subject_id}/{session_id}/dwi/{subject_id}_{session_id}_acq-DKI64DIRECTIONSAP3WEIGHTSAX_dwi.nii.gz', \
    'bvals' : ipdir+'{subject_id}/{session_id}/dwi/{subject_id}_{session_id}_acq-DKI64DIRECTIONSAP3WEIGHTSAX_dwi.bval', \
    'bvecs' : ipdir+'{subject_id}/{session_id}/dwi/{subject_id}_{session_id}_acq-DKI64DIRECTIONSAP3WEIGHTSAX_dwi.bvec'
    }

    selectfiles = pe.Node(nio.SelectFiles(templates,base_directory=ipdir),name="selectfiles")

    datasink = pe.Node(nio.DataSink(base_directory=globaldir, container=workdir),name="datasink")


    diff_qc=create_diff_qc()

    qc.connect([

        (infosource,selectfiles,[('subject_id', 'subject_id'),('session_id', 'session_id')]),
        
        (selectfiles,diff_qc,[('dki','inputspec.diff')]),      
        (selectfiles, diff_qc, [('bvals', 'inputspec.bvals')]),
        (selectfiles, diff_qc, [('bvecs', 'inputspec.bvecs')]),
        (diff_qc, datasink, [('outputspec.diffnrrd','@dwi')]),
        (diff_qc, datasink, [('outputspec.outputFolder','@dwiqc/')]),
        (diff_qc, datasink, [('outputspec.faMap','@famaptest/')])
        

    ])


    qc.run('MultiProc',plugin_args={'n_procs':4})
    qc.write_graph()