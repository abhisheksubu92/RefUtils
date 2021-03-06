#! /usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author  : MG
@Time    : 2019/03/19 16:09
@File    : LSTMRNN_classification_demo.py
@contact : mmmaaaggg@163.com
@desc    : 输入双sin曲线，输出cos曲线未来波动是否可能超过 -0.1或 0.1
"""
import tensorflow as tf
import numpy as np
# from tensorflow.examples.tutorials.mnist import input_data
import matplotlib.pyplot as plt
import itertools


# mnist = input_data.read_data_sets("MNIST_data", one_hot=True)
BATCH_START = 0
TIME_STEPS = 20
BATCH_SIZE = 50
INPUT_SIZE = 2
OUTPUT_SIZE = 2
CELL_SIZE = 10
LR = 0.006
BATCH_START_TEST = 0


def get_label_by_future_value(value_arr: np.ndarray, min_pct: float, max_pct: float, max_future=None):
    """
    根据时间序列数据 pct_arr 计算每一个时点目标标示 -1 0 1
    计算方式：当某一点未来波动首先 >（ 或 <） 上届 min_pct（或下届 max_pct），则标记为 1 （或 -1）
    :param value_arr:
    :param min_pct:
    :param max_pct:
    :param max_future:最大搜索长度
    :return:
    """
    value_arr[np.isnan(value_arr)] = 0
    arr_len = value_arr.shape[0]
    target_arr = np.zeros((arr_len, OUTPUT_SIZE))
    for i in range(arr_len):
        base = value_arr[i]
        for j in range(i+1, arr_len):
            result = value_arr[j] / base - 1
            if result < min_pct:
                target_arr[i, 0] = 1
                break
            elif result > max_pct:
                target_arr[i, 1] = 1
                break
    return target_arr


def get_batch(show_plt=False):
    """
    够在一系列输入输出数据集
    xs： 两条同频率，不同位移的sin曲线
    ys_value： 目标是一条cos曲线
    ys: ys_value 未来涨跌标识
    i_s：X 序列
    """
    global BATCH_START, TIME_STEPS
    # i_s shape(50 batch, 20 steps)
    i_s = np.arange(BATCH_START, BATCH_START + TIME_STEPS * BATCH_SIZE).reshape((BATCH_SIZE, TIME_STEPS))
    inputs = np.zeros((BATCH_SIZE, TIME_STEPS, INPUT_SIZE))
    inputs[:, :, 0] = i_s
    inputs[:, :, 1] = i_s - 0.5
    # xs = np.zeros((BATCH_SIZE, TIME_STEPS, 2))
    # xs[:, :, 0] = np.sin(i_s)
    # xs[:, :, 1] = np.sin(i_s - 0.5)
    xs = np.sin(inputs)
    # 为了生成 label 需要用到future数据，因此多生成一行数据共生成对应的 label 使用
    xs_4_res = np.arange(BATCH_START, BATCH_START + TIME_STEPS * (BATCH_SIZE + 1))
    ys_value = np.cos(xs_4_res) + 5
    ys = get_label_by_future_value(ys_value, -0.1, 0.1)
    ys = ys[range(TIME_STEPS + 1, TIME_STEPS * BATCH_SIZE + 2, TIME_STEPS), :]
    BATCH_START += TIME_STEPS
    if show_plt:
        plt.plot(i_s[0, :], ys_value[0, :], 'r',
                 i_s[0, :], xs[0, :, 0], 'b--',
                 i_s[0, :], xs[0, :, 1], 'b',
                 i_s[0, :], ys[:, 0] * (-1) + ys[:, 1], 'r',
                 )
        plt.show()
    # returned xs, ys_value and shape (batch, step, input)
    return xs, ys, i_s


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
        # X (128 batch, 28 steps, 28 inputs)
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
        self.l_out_x = tf.unstack(tf.transpose(self.cell_outputs, [1, 0, 2]))  # states is the last outputs
        self.Ws_out = tf.Variable(tf.random_normal([self.n_hidden_units, self.n_classes]))
        self.bs_out = tf.Variable(tf.constant(0.1, shape=[self.n_classes, ]))
        self.pred = tf.matmul(self.l_out_x[-1], self.Ws_out) + self.bs_out

    def compute_cost(self):
        self.cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(
            logits=self.pred, labels=self.ys))
        tf.summary.scalar('cost', self.cost)


def train():
    # hyperparameters
    lr = LR
    training_iters = 100000
    batch_size = BATCH_SIZE

    n_inputs = INPUT_SIZE  # MNIST data input (img shape 28*28)
    n_step = TIME_STEPS  # time steps
    n_hidden_units = CELL_SIZE  # neurons in hidden layer
    n_classes = OUTPUT_SIZE  # MNIST classes (0-9 digits)
    model = LSTMRNN(n_step, n_inputs, n_hidden_units, n_classes, lr, batch_size)
    with tf.Session() as sess:
        merged = tf.summary.merge_all()
        writer = tf.summary.FileWriter('logs', sess.graph)
        # relocate to the local dir and run this line to view it on Chrome(http://0.0.0.0:6006/):
        # $ tensorboard --logdir='logs'

        sess.run(tf.global_variables_initializer())
        step = 0
        while step * model.batch_size < training_iters:
            # batch_xs, batch_ys = mnist.train.next_batch(model.batch_size)
            # batch_xs.shape, batch_ys.shape
            batch_xs, batch_ys, _ = get_batch()
            # batch_xs = batch_xs.reshape([model.batch_size, model.n_step, model.n_inputs])
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

            # sess.run(model.train_op, feed_dict=feed_dict)
            _, cost, state, pred = sess.run(
                [model.train_op, model.cost, model.cell_final_state, model.pred]
                , feed_dict=feed_dict
            )

            if step % 20 == 0:
                # batch_xs, batch_ys, _ = get_batch()
                # if step == 0:
                #     feed_dict = {
                #         model.xs: batch_xs,
                #         model.ys: batch_ys,
                #         # create initial state
                #     }
                # else:
                #     feed_dict = {
                #         model.xs: batch_xs,
                #         model.ys: batch_ys,
                #         model.cell_init_state: state,  # use last state as the initial state for this run
                #     }
                print(sess.run(model.accuracy_op, feed_dict=feed_dict))
                result = sess.run(merged, feed_dict)
                writer.add_summary(result, step)

            step += 1


if __name__ == '__main__':
    train()
