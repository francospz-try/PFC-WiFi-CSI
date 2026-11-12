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

    def test_recognition_and_link_captures_never_teach_even_if_labeled(self):
        self.record('a','quieto');self.record('b','caminar')
        for name,use in [('reserved','reconocer'),('link','enlace')]:
            p=self.record(name,'caminar')
            meta=json.loads((p/'metadata.json').read_text());meta['capture_use']=use
            (p/'metadata.json').write_text(json.dumps(meta))
        report=train(self.root,self.out,'binario','prueba')
        self.assertEqual(report['sessions'],['a','b'])
        self.assertIsNone(report['evaluation'])

    def test_prediction_identifies_model_and_declared_activity(self):
        import hashlib
        self.record('a','quieto');self.record('b','caminar')
        train(self.root,self.out,'binario','prueba')
        p=self.record('fresh','sin_etiquetar')
        meta=json.loads((p/'metadata.json').read_text());meta['declared_activity']='sentado'
        (p/'metadata.json').write_text(json.dumps(meta))
        result=predict(p,self.out,'binario')
        self.assertEqual(result.get('model_dataset'),'prueba')
        self.assertEqual(result.get('model_mode'),'binario')
        self.assertEqual(result.get('model_sha256'),hashlib.sha256((self.out/'binario.npz').read_bytes()).hexdigest())
        self.assertEqual(result.get('declared_activity'),'sentado')

    def test_new_model_records_utc_training_time(self):
        from datetime import datetime, timezone
        self.record('a','quieto');self.record('b','caminar')
        before=datetime.now(timezone.utc)
        report=train(self.root,self.out,'binario','prueba')
        self.assertIsNotNone(report.get('trained_at_utc'))
        stamp=datetime.fromisoformat(report['trained_at_utc'])
        self.assertIsNotNone(stamp.tzinfo)
        self.assertGreaterEqual(stamp,before)
        self.assertLessEqual(stamp,datetime.now(timezone.utc))

    def test_prediction_hash_identifies_the_bytes_used_during_concurrent_replacement(self):
        import hashlib
        from unittest.mock import patch
        from src.pfc07.csi_reconocimiento import infer
        self.record('a','quieto');self.record('b','caminar')
        train(self.root,self.out,'binario','prueba')
        fresh=self.record('fresh','sin_etiquetar')
        model_path=self.out/'binario.npz'
        original_hash=hashlib.sha256(model_path.read_bytes()).hexdigest()
        def replace_after_load(x,model,classes):
            # Simulate another writer atomically replacing the file after loading.
            replacement=self.out/'replacement.npz'
            np.savez(replacement,mean=model[0]+1,scale=model[1],centers=model[2])
            replacement.replace(model_path)
            return infer(x,model,classes)
        with patch('src.pfc07.csi_reconocimiento.infer',side_effect=replace_after_load):
            result=predict(fresh,self.out,'binario')
        self.assertNotEqual(hashlib.sha256(model_path.read_bytes()).hexdigest(),original_hash)
        self.assertEqual(result['model_sha256'],original_hash)
