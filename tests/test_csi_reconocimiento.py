import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import numpy as np
from src.pfc07.csi_reconocimiento import train,predict,features

class RecognitionTest(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'sessions';self.root.mkdir();self.out=Path(self.tmp.name)/'models'
    def record(self,name,label,rate=89,posture='de_pie_lateral'):
        p=self.root/name;p.mkdir()
        meta=dict(session=name,dataset='prueba',room='habitacion',label=label,posture=posture,
                  quality=dict(valid_csi=1000,observed_hz=rate,sequence_gaps=0,malformed_csi=0))
        (p/'metadata.json').write_text(json.dumps(meta))
        lines=[]
        for i in range(900):
            a=20+int((8 if label=='caminar' else 1)*np.sin(i*.2))
            v=[a,3]*128
            lines.append(f'CSI_DATA,{i},mac,-74,0,0,0,0,11,{i*11000},0,0,256,0,"{v}"')
        (p/'raw.log').write_text('\n'.join(lines))
        return p
    def test_demo_no_accuracy_and_no_training_reuse(self):
        a=self.record('a','quieto');self.record('b','caminar')
        r=train(self.root,self.out,'binario','prueba')
        self.assertIsNone(r['evaluation'])
        with self.assertRaises(ValueError): predict(a,self.out,'binario')
        fresh=self.record('fresh','sin_etiquetar')
        result=predict(fresh,self.out,'binario')
        self.assertAlmostEqual(sum(result['percentages'].values()),100)
    def test_holdout_is_by_recording(self):
        for n,label in [('a','quieto'),('b','caminar'),('c','quieto'),('d','caminar')]: self.record(n,label)
        r=train(self.root,self.out,'binario','prueba')['evaluation']
        self.assertFalse(set(r['training'])&set(r['test']))
        self.assertEqual(len(r['test']),2)
    def test_low_quality_rejected_and_missing_posture(self):
        p=self.record('poor','quieto',rate=27)
        with self.assertRaises(ValueError): features(p)
        self.record('walk','caminar')
        with self.assertRaises(ValueError): train(self.root,self.out,'posturas','prueba')
