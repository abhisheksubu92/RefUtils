#! /usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author  : MG
@Time    : 19-2-19 上午9:26
@File    : session_demo
@contact : mmmaaaggg@163.com
@desc    :  session function demo
"""
import tensorflow as tf

matrix1 = tf.constant([[3, 3]])
matrix2 = tf.constant([[2], [2]])

product = tf.matmul(matrix1, matrix2)  # matrix multiply np.dot(m1, m2)

# method1
sess = tf.Session()
result = sess.run(product)
print(result)

sess.close()

# method 2
with tf.Session() as sess:
    result2 = sess.run(product)
    print(result2)


