import cv2
import numpy as np
import onnxruntime
from PySide6.QtCore import QDir


class TextRecInfer(object):
    # instance: "TextRecInfer" = None

    # def __new__(cls) -> Self:
    #     if cls.instance is None:
    #         cls.instance = TextRecInfer()
    #     return cls.instance

    def __init__(self) -> None:
        model_dir = QDir("model:onnx_crnnS05/")
        model = model_dir.filePath("latest.onnx")

        infer_dict = model_dir.filePath("dict.txt")
        self.dict = []
        self.dict.append("")
        with open(infer_dict, "r", encoding="utf8") as f:
            for x in f:
                self.dict.append(x.strip())
        self.dict.append(" ")

        self.sess = onnxruntime.InferenceSession(model)

    def predict(self, img: cv2.Mat, bounds: list | np.ndarray):
        resize_imgs = self._preprocess(img, bounds)

        (output,) = self.sess.run(None, {"input": resize_imgs})

        return self._postprocess(output)[0]

    def _preprocess(self, img: cv2.Mat, bounds: list | np.ndarray):
        resize_h = 32
        resize_w = 320

        resize_imgs = []
        for l, t, r, b in bounds:
            crop_img = img[t:b, l:r, :]
            imgh, imgw = crop_img.shape[:2]
            new_h = resize_h
            new_w = int(new_h * imgw // imgh)
            if new_w > resize_w:
                new_w = resize_w
            crop_img = cv2.cvtColor(crop_img, cv2.COLOR_BGRA2GRAY)
            crop_img = cv2.resize(crop_img, (new_w, new_h))
            crop_img = cv2.adaptiveThreshold(
                crop_img,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                new_h + new_h % 2 - 1,
                2,
            )
            # cv2.imshow('w', crop_img)
            # cv2.waitKey(0)
            crop_img = crop_img.astype(np.float32)
            crop_img = (crop_img / 255.0 - 0.5) / 0.5
            if new_w < resize_w:
                crop_img = np.pad(
                    crop_img,
                    ((0, 0), (0, resize_w - new_w)),
                    mode="constant",
                    constant_values=0.0,
                )
            crop_img = np.expand_dims(crop_img, axis=0)
            resize_imgs.append(crop_img)
        return np.array(resize_imgs, dtype=np.float32)

    def _postprocess(self, x: np.ndarray, cal_confidence=True):
        # argmax_start_time = time.time()
        xidx = np.argmax(x, axis=2)

        xval = None
        if cal_confidence:
            xval = np.max(x, axis=2)
        # argmax_end_time = time.time()

        # itr_timestep_start = time.time()
        result = []
        result_conf = []
        for b in range(len(x)):
            txt = ""
            min_conf = None
            data = xidx[b]
            dataidx = data[np.where(np.diff(data, prepend=0) != 0)[0]]
            for idx in dataidx:
                txt += self.dict[idx]

            if xval is not None:
                min_conf = np.min(xval[b])
            else:
                min_conf = 0

            result.append(txt)

            if cal_confidence:
                result_conf.append(float(min_conf))
        # itr_timestep_end = time.time()

        # print(
        #     f"argmax_time:{argmax_end_time - argmax_start_time} "
        #     f"itr_timestep_time:{itr_timestep_end - itr_timestep_start}"
        # )

        return result, result_conf
