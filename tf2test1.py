import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, optimizers, datasets
from tensorflow.keras import losses

# gpus = tf.config.experimental.list_physical_devices(device_type='GPU')
# print(gpus)
print(tf.config.list_physical_devices('GPU'))
#收集数据，预处理
(x, y), (x_val, y_val) = datasets.mnist.load_data()
# print(x[0])
x = tf.convert_to_tensor(x, dtype=tf.float32) / 255.
y = tf.convert_to_tensor(y, dtype=tf.int32)
# y = tf.one_hot(y, depth=10)
print(x.shape, y.shape)

train_dataset = tf.data.Dataset.from_tensor_slices((x, y))
train_dataset = train_dataset.batch(200)
#定义模型
model = keras.Sequential([
    layers.Flatten(),
    layers.Dense(512, activation='relu'),
    layers.Dense(256, activation='relu'),
    layers.Dense(10,activation='softmax'),
    # layers.Softmax()
])#,activation=tf.nn.softmax)])


# model = tf.keras.models.Sequential([
#     layers.Reshape(target_shape = [28,28,1],input_shape = (28,28,)), # [batch_size,28,28,] ->[batch_size,28,28,1]
#     tf.keras.layers.Conv2D(64, (3, 3), activation='relu', input_shape=(28, 28, 1)),
#     tf.keras.layers.MaxPooling2D(2, 2),
#     tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
#     tf.keras.layers.MaxPooling2D(2, 2),
#     tf.keras.layers.Flatten(),
#     tf.keras.layers.Dense(512, activation=tf.nn.relu),
#     tf.keras.layers.Dense(10, activation=tf.nn.softmax)
# ])

# layers.CRF

model.build(input_shape=[200,28,28])
model.summary()
#定义优化器
optimizer = optimizers.SGD(learning_rate=0.01)
#y_pred 表示网络的预测值，当 from_logits 设置为 True 时，
#y_pred 表示须为未经过 Softmax 函数的变量 z；当 from_logits 设置为 False 时， y_pred 表示
#为经过 Softmax 函数的输出。
lossfun=losses.SparseCategoricalCrossentropy(from_logits=True)
# categorical_accuracy = tf.keras.metrics.CategoricalAccuracy()
categorical_accuracy = tf.keras.metrics.SparseCategoricalAccuracy()
checkpoint=  tf.train.Checkpoint(savemode=model)
manager = tf.train.CheckpointManager(checkpoint, directory='./checkpoint', max_to_keep=3,checkpoint_name='mnist.ckpt')

# summary_writer = tf.summary.create_file_writer('./tensorboard')

# tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir='my_log_dir', histogram_freq=1)
tensorboard_callback  = [
 keras.callbacks.TensorBoard(
 log_dir='my_log_dir',  	#日志文件将被写入这个位置
 histogram_freq=1	#每一轮之后记录激活直方图
 )
]


def fastway():

    #这个模式就会快得多，也简单得多，不用下面那么多。
    model.compile(
        optimizer=optimizer,
        loss=lossfun,
        metrics=[categorical_accuracy]
    )
    try:
        pass
        # checkpoint.restore(tf.train.latest_checkpoint('./checkpoint'))
    except:
        pass

    model.fit(train_dataset,
              batch_size=200,
              epochs=30,
              validation_data=(x_val,y_val),
              # callbacks=tensorboard_callback
    )
    model.summary()
    # checkpoint.save('./checkpoint/mnist.ckpt')
    manager.save()
    # model.save('./mod/mnist')

def loadModel():

    tf.saved_model.load('./mod/mnist')
    model.fit(train_dataset,
              batch_size=200,
              epochs=1,
              validation_data=(x_val, y_val)

              )

    model.summary()

def restore():
    model.compile(
        optimizer=optimizer,
        loss=lossfun,
        metrics=[categorical_accuracy]
    )

    checkpoint.restore(tf.train.latest_checkpoint('./checkpoint'))
    model.evaluate(x=x_val,y=y_val)
    model.summary()

#迭代次数据
def train_epoch(epoch):
    # Step4.loop
    train_dataset.shuffle(20)
    #分批，每批200
    for step, (x, y) in enumerate(train_dataset):
        #梯度环境记录
        with tf.GradientTape() as tape:
            y1 = tf.argmax(y, axis=1)
            # [b, 28, 28] => [b, 784]  b是指batch=200,也就是200张
            #打平输入
            # x = tf.reshape(x, (-1, 28 * 28))
            # Step1. compute output
            # [b, 784] => [b, 10]
            #输入模型
            out = model(x)
            # Step2. compute loss
            #计算损失,
            # loss = tf.reduce_sum(tf.square(out - y)) / x.shape[0]
            # loss = tf.keras.losses.sparse_categorical_crossentropy(y_true=y1,y_pred=out)#试一个新的
            # loss = tf.reduce_mean(loss)
            # 现已从上面这种改成对像式的，直接reduce_mean过了
            loss=lossfun(y_true=y1,y_pred=out)
            print(out.numpy()[0])
            # print(y.shape,out.shape)

            out1=tf.argmax(out,axis=1)
            # print(y1,out1)
            categorical_accuracy.update_state(y_true=y1, y_pred=out)
        # Step3. optimize and update w1, w2, w3, b1, b2, b3
        grads = tape.gradient(loss, model.trainable_variables)
        # w' = w - lr * grad
        optimizer.apply_gradients(zip(grads, model.trainable_variables))

        if step % 100 == 0:
            print(epoch, step, 'loss:', loss.numpy())
            print("test accuracy: %f" % categorical_accuracy.result())


def train():
    for epoch in range(30):
        train_epoch(epoch)


if __name__ == '__main__':
    # pass
    fastway()
    # train()
    # loadModel()
    # restore()