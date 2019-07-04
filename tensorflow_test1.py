import tensorflow as tf

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
pd. gl
# state=tf.Variable(0,name='counter')
#
# one=tf.constant(1)
# new_value=tf.add(state,one)
# update=tf.assign(state,new_value)
#
# # init=tf.initialize_all_variables()
# init=tf.global_variables_initializer()
#
# with tf.Session() as sess:
#     sess.run(init)
#     for i in range(3):
#         sess.run(update)
#         print(sess.run(state))
#
#
# input1=tf.placeholder(tf.float32)
# input2=tf.placeholder(tf.float32)
#
# output=tf.multiply(input1,input2)
# with tf.Session() as sess:
#     print(sess.run(output,feed_dict={input1:[7],input2:[3]}))


def add_layer(inputs,in_size,out_size,activcation_function=None):
    Weights=tf.Variable(tf.random_normal([in_size,out_size]))
    biases=tf.Variable(tf.zeros([1,out_size])+0.1)
    Wx_plus_b=tf.matmul(inputs,Weights)+biases
    if activcation_function is None:
        outputs=Wx_plus_b
    else:
        outputs=activcation_function(Wx_plus_b)
    return outputs

x_data=np.linspace(-1,1,300)[:,np.newaxis]
noise=np.random.normal(0,0.05,x_data.shape)
y_data=np.square(x_data)-0.5

xs=tf.placeholder(tf.float32,[None,1])
ys=tf.placeholder(tf.float32,[None,1])

l1=add_layer(xs,1,10,activcation_function=tf.nn.relu)
predition=add_layer(l1,10,1,activcation_function=None)

loss=tf.reduce_mean(tf.reduce_sum( tf.square(ys-predition),reduction_indices=[1]))

train_step=tf.train.GradientDescentOptimizer(learning_rate=0.1).minimize(loss)

init=tf.global_variables_initializer()

with tf.Session() as sess:
    sess.run(init)
    fig=plt.figure()
    plt.subplot(1,1,1)
    plt.scatter(x_data,y_data)
    plt.show()

    for i in range(8000):
        sess.run(train_step,feed_dict={xs:x_data,ys:y_data})
        if i%20==0:
            print(sess.run(loss,feed_dict={xs:x_data,ys:y_data}))

'''
tensorboard --logdir output
'''
writer=tf.summary.FileWriter('./output',sess.graph)
writer.close()

