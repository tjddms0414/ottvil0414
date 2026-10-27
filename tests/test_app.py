import io
import json
import unittest
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from app import app, refine_alpha, brighten_product
import numpy as np
import cv2

class StudioTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        im = Image.new('RGB', (400, 400), (80, 130, 180))
        ImageDraw.Draw(im).rounded_rectangle((130, 70, 270, 330), radius=20, fill=(210, 60, 40))
        buf = io.BytesIO()
        im.save(buf, 'PNG')
        self.data = buf.getvalue()

    def test_white_background_and_original_product_pixels(self):
        r = self.client.post('/api/process', files={'file': ('photo.png', self.data, 'image/png')}, data={'selection': json.dumps(dict(x=.25,y=.1,w=.5,h=.8)), 'shadow': '0', 'brightness': '0'})
        self.assertEqual(r.status_code,200,r.text if r.status_code!=200 else '')
        im = Image.open(io.BytesIO(r.content))
        self.assertEqual(im.size, (400,400))
        self.assertEqual(im.getpixel((200,200)), (210,60,40))
        self.assertEqual(im.getpixel((0,0)), (255,255,255))

    def test_brush_preserves_selected_background_as_foreground(self):
        strokes = [{'mode':'keep','size':.04,'points':[[.18,.5]]}, {'mode':'remove','size':.03,'points':[[.5,.5]]}]
        r = self.client.post('/api/process',files={'file':('photo.png',self.data)}, data={'selection':json.dumps(dict(x=.1,y=.1,w=.8,h=.8)),'strokes':json.dumps(strokes),'shadow':'0','brightness':'0'})
        self.assertEqual(r.status_code,200)
        im=Image.open(io.BytesIO(r.content))
        self.assertEqual(im.getpixel((72,200)),(80,130,180))
        self.assertEqual(im.getpixel((200,200)),(255,255,255))

    def test_brightness_lifts_midtones_and_preserves_endpoints(self):
        im = Image.new('RGB', (1,1), (0,100,255))
        self.assertEqual(brighten_product(im,0).getpixel((0,0)), (0,100,255))
        pixel = brighten_product(im,30).getpixel((0,0))
        self.assertEqual(pixel[0],0)
        self.assertGreater(pixel[1],100)
        self.assertEqual(pixel[2],255)

    def test_edge_cleanup_removes_dust_preserves_brush(self):
        mask=np.zeros((100,100),np.uint8)
        mask[20:80,20:80]=cv2.GC_PR_FGD
        mask[5,5]=cv2.GC_PR_FGD
        mask[8,8]=cv2.GC_FGD
        rgb=np.full((100,100,3),120,np.uint8)
        alpha=np.array(refine_alpha(mask,rgb,1))
        self.assertEqual(alpha[5,5],0)
        self.assertEqual(alpha[8,8],255)
        self.assertEqual(alpha[50,50],255)
        self.assertLess(alpha[20,50],255)

    def test_brightness_applies_only_to_product(self):
        r=self.client.post('/api/process',files={'file':('photo.png',self.data)},data={'selection':json.dumps(dict(x=.25,y=.1,w=.5,h=.8)),'shadow':'0','brightness':'30'})
        self.assertEqual(r.status_code,200)
        im=Image.open(io.BytesIO(r.content))
        self.assertGreater(im.getpixel((200,200))[1],60)
        self.assertEqual(im.getpixel((0,0)),(255,255,255))

    def test_invalid_inputs(self):
        r=self.client.post('/api/process',files={'file':('bad.png',b'bad')},data={'selection':'{}'})
        self.assertEqual(r.status_code,400)
        r=self.client.post('/api/process',files={'file':('photo.png',self.data)},data={'selection':json.dumps(dict(x=0,y=0,w=0,h=0))})
        self.assertEqual(r.status_code,400)

if __name__ == '__main__': unittest.main()
