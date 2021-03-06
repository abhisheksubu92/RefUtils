#! /usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author  : MG
@Time    : 2019/02/22 上午10:09
@File    : rnn_classification_demo.py
@contact : mmmaaaggg@163.com
@desc    : 
"""
import tensorflow as tf
import numpy as np
from tensorflow.examples.tutorials.mnist import input_data

mnist = input_data.read_data_sets("MNIST_data", one_hot=True)


class LSTMRNN:
    def __init__(self, n_step, n_inputs, n_hidden_units, n_classes, lr, batch_size):
        """

        :param n_step: time steps
        :param n_inputs: MNIST data input (img shape 28*28)
        :param n_hidden_units: neurons in hidden layer
        :param n_classes: MNIST classes (0-9 digits)
        :param lr:
        :param training_iters:
        :param batch_size:
        """
        self.n_step = n_step
        self.n_inputs = n_inputs
        self.n_hidden_units = n_hidden_units
        self.n_classes = n_classes
        # hyperparameters
        self.lr = lr
        self.batch_size = batch_size
        # attributes defined in other functions
        self.cost = None
        self.l_in_y = None
        self.cell_outputs = None
        self.cell_init_state = None
        self.cell_final_state = None

        with tf.name_scope('inputs'):
            # tf Graph input
            self.xs = tf.placeholder(tf.float32, [None, n_step, n_inputs])
            self.ys = tf.placeholder(tf.float32, [None, n_classes])

        # Define weights
        self.weights = {
            # 28*128
            'in': tf.Variable(tf.random_normal([n_inputs, n_hidden_units])),
            # (128, 10)
            'out': tf.Variable(tf.random_normal([n_hidden_units, n_classes]))
        }

        self.biases = {
            # (128, )
            'in': tf.Variable(tf.constant(0.1, shape=[n_hidden_units, ])),
            # (10, )
            'out': tf.Variable(tf.constant(0.1, shape=[n_classes, ]))
        }
        with tf.variable_scope('in_hidden'):
            self.add_input_layer()
        with tf.variable_scope('LSTM_cell'):
            self.add_cell()
        with tf.variable_scope('out_hidden'):
            self.add_output_layer()
        with tf.name_scope('cost'):
            self.compute_cost()
        with tf.name_scope('train'):
            self.train_op = tf.train.AdamOptimizer(self.lr).minimize(self.cost)
        with tf.name_scope('accuracy'):
            correct_pred = tf.equal(tf.argmax(self.pred, 1), tf.argmax(self.ys, 1))
            self.accuracy_op = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

    def add_input_layer(self):
        # hidden layer for input to cell
        # X (128, batch, 28 steps, 28 inputs)
        # ==> X (128 * 28, 28 inputs)
        l_in_x = tf.reshape(self.xs, [-1, self.n_inputs])
        Ws_in = tf.Variable(tf.random_normal([self.n_inputs, self.n_hidden_units]))
        bs_in = tf.Variable(tf.constant(0.1, shape=[self.n_hidden_units, ]))
        # ==> X_in (128 batch * 28 steps, 128 hidden)
        with tf.name_scope('Wx_plus_b'):
            l_in_y = tf.matmul(l_in_x, Ws_in) + bs_in
        # ==> X_in (128 batch, 28 steps, 128 hidden)
        self.l_in_y = tf.reshape(l_in_y, [-1, self.n_step, self.n_hidden_units])

    def add_cell(self):
        # cell
        lstm_cell = tf.nn.rnn_cell.BasicLSTMCell(self.n_hidden_units, forget_bias=1.0, state_is_tuple=True)
        with tf.name_scope('initial_state'):
            # lstm cell is divided into two parts (c_state, m_state)
            self.cell_init_state = lstm_cell.zero_state(self.batch_size, dtype=tf.float32)

        self.cell_outputs, self.cell_final_state = tf.nn.dynamic_rnn(lstm_cell, self.l_in_y, initial_state=self.cell_init_state, time_major=False)

    def add_output_layer(self):
        # hidden layer for output as the final results
        # method 1
        # results = tf.matmul(states[1], weights['out']) + biases['out']  # states[1] is m_state
        # method 2
        # unpack to list[(batch, outputs)...] * steps
        l_out_x = tf.unstack(tf.transpose(self.cell_outputs, [1, 0, 2]))  # states is the last outputs
        Ws_out = tf.Variable(tf.random_normal([self.n_hidden_units, self.n_classes]))
        bs_out = tf.Variable(tf.constant(0.1, shape=[self.n_classes, ]))
        self.pred = tf.matmul(l_out_x[-1], Ws_out) + bs_out

    def compute_cost(self):
        self.cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(
            logits=self.pred, labels=self.ys))
        tf.summary.scalar('cost', self.cost)


def train():
    # hyperparameters
    lr = 0.001
    training_iters = 100000
    batch_size = 128

    n_inputs = 28  # MNIST data input (img shape 28*28)
    n_step = 28  # time steps
    n_hidden_units = 128  # neurons in hidden layer
    n_classes = 10  # MNIST classes (0-9 digits)
    model = LSTMRNN(n_step, n_inputs, n_hidden_units, n_classes, lr, batch_size)
    with tf.Session() as sess:
        merged = tf.summary.merge_all()
        writer = tf.summary.FileWriter('logs', sess.graph)
        # relocate to the local dir and run this line to view it on Chrome(http://0.0.0.0:6006/):
        # $ tensorboard --logdir='logs'

        sess.run(tf.global_variables_initializer())
        step = 0
        while step * model.batch_size < training_iters:
            batch_xs, batch_ys = mnist.train.next_batch(model.batch_size)
            batch_xs = batch_xs.reshape([model.batch_size, model.n_step, model.n_inputs])
            # feed_dict = {model.xs: batch_xs, model.ys: batch_ys}
            # sess.run(model.train_op, feed_dict=feed_dict)
            if step == 0:
                feed_dict = {
                    model.xs: batch_xs,
                    model.ys: batch_ys,
                    # create initial state
                }
            else:
                feed_dict = {
                    model.xs: batch_xs,
                    model.ys: batch_ys,
                    model.cell_init_state: state,  # use last state as the initial state for this run
                }

            _, cost, state, pred = sess.run(
                [model.train_op, model.cost, model.cell_final_state, model.pred]
                , feed_dict=feed_dict
            )

            if step % 20 == 0:
                print(sess.run(model.accuracy_op, feed_dict=feed_dict))
                result = sess.run(merged, feed_dict)
                writer.add_summary(result, step)

            step += 1


if __name__ == '__main__':
    train()
