import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn import datasets

scikit_iris=datasets.load_iris()
iris=pd.DataFrame(
    data=np.c_[scikit_iris['data'],scikit_iris['target']],
    columns=np.append(scikit_iris.feature_names,['y'])
)
print(iris.head())
print(iris.isnull().sum())
print(iris.groupby('y').count())

X=iris[scikit_iris.feature_names]
y=iris['y']

from sklearn.neighbors import KNeighborsClassifier
knn=KNeighborsClassifier(n_neighbors=1)
knn.fit(X,y)
p=knn.predict([[3,2,2,4]])
print(p)
#replace
# from sklearn.cross_validation import train_test_split

from sklearn.model_selection import train_test_split
from sklearn import metrics

X_train,X_test,y_train,y_test=train_test_split(X,y,random_state=4)
print(len(X_train))

knn=KNeighborsClassifier(n_neighbors=15)
knn.fit(X_train,y_train)
y_pred_on_train=knn.predict(X_train)
y_pred_on_test=knn.predict(X_test)


print('{}'.format(metrics.accuracy_score(y_test,y_pred_on_test)))

from abupy import AbuML
iris=AbuML.create_test_fiter()
iris.estimator.knn_classifier(n_neighbors=15)
print(iris.cross_val_accuracy_score())


y=np.poly1d([1,0,0])
d_yx=np.polyder(y)
print(d_yx(-7))

f1=np.array([0.2,0.5,1.1]).reshape(-1,1)
f2=np.array([-100,56,-77]).reshape(-1,1)
print(f1,f2)

import sklearn.preprocessing as prep
scaler=prep.StandardScaler()
f1_scaled=scaler.fit_transform(f1)
f2_scaled=scaler.fit_transform(f2)
print(f1_scaled,f2_scaled)
