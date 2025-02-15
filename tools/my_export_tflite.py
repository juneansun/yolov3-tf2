import time
from absl import app, flags, logging
from absl.flags import FLAGS
import cv2
import numpy as np
import tensorflow as tf
from yolov3_tf2.models import (
    YoloV3, YoloV3Tiny
)
from yolov3_tf2.dataset import transform_images

from tensorflow.python.eager import def_function
from tensorflow.python.framework import tensor_spec
from tensorflow.python.util import nest

from tensorflow.python.ops.numpy_ops import np_config
np_config.enable_numpy_behavior()

flags.DEFINE_string('weights', './checkpoints/yolov3.tf',
                    'path to weights file')
flags.DEFINE_boolean('tiny', False, 'yolov3 or yolov3-tiny')
flags.DEFINE_string('output', './checkpoints/yolov3.tflite',
                    'path to saved_model')
flags.DEFINE_string('classes', './data/coco.names', 'path to classes file')
flags.DEFINE_string('image', './data/girl.png', 'path to input image')
flags.DEFINE_integer('num_classes', 80, 'number of classes in the model')
flags.DEFINE_integer('size', 416, 'image size')


def main(_argv):
    if FLAGS.tiny:
        yolo = YoloV3Tiny(size=FLAGS.size, classes=FLAGS.num_classes)
    else:
        yolo = YoloV3(size=FLAGS.size, classes=FLAGS.num_classes)

    yolo.load_weights(FLAGS.weights)
    logging.info('weights loaded')

    def representative_data_gen():
        r_img = tf.image.decode_image(open(FLAGS.image, 'rb').read(), channels=3)
        r_img = tf.expand_dims(r_img, 0)
        r_img = transform_images(r_img, 416)
        yield [r_img]

    converter = tf.lite.TFLiteConverter.from_keras_model(yolo)

    # Fix from https://stackoverflow.com/questions/64490203/tf-lite-non-max-suppression
    converter.experimental_new_converter = True
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.representative_dataset = representative_data_gen
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    # converter.inference_input_type = tf.uint8
    converter.inference_output_type = tf.uint8

    tflite_model = converter.convert()
    open(FLAGS.output, 'wb').write(tflite_model)
    logging.info("model saved to: {}".format(FLAGS.output))

    interpreter = tf.lite.Interpreter(model_path=FLAGS.output)
    interpreter.allocate_tensors()
    logging.info('tflite model loaded')

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    class_names = [c.strip() for c in open(FLAGS.classes).readlines()]
    logging.info('classes loaded')

    img = tf.image.decode_image(open(FLAGS.image, 'rb').read(), channels=3)
    img = tf.expand_dims(img, 0)
    img = transform_images(img, 416)
    logging.info('image transformed')


    t1 = time.time()
    # outputs = interpreter.set_tensor(input_details[0]['index'], img.astype(np.uint8))
    outputs = interpreter.set_tensor(input_details[0]['index'], img)
    t2 = time.time()
    logging.info('time: {}'.format(t2 - t1))

    interpreter.invoke()

    output_data = interpreter.get_tensor(output_details[0]['index'])

    print(output_data)

if __name__ == '__main__':
    app.run(main)
