import numpy as np


def point_to_np(point):
    return np.array([point['x'], point['y'], point['z']])


def transform_to_mat(transform):
    # T should represent world coord in local

    T = np.array([[transform['x_axis']['x'], transform['x_axis']['y'], transform['x_axis']['z'], transform['origin']['x']],
                 [transform['y_axis']['x'], transform['y_axis']['y'], transform['y_axis']['z'], transform['origin']['y']],
                 [transform['z_axis']['x'], transform['z_axis']['y'], transform['z_axis']['z'], transform['origin']['z']],

                 [0, 0, 0, 1]])

    return T

def transform_print(transform):
    T = transform_to_mat(transform)
    return T.tolist()


def transform_pt(point, transform):
    # transform the point on the given local plane to world coord

    # print('hw', point)
    # print('transform', transform)

    tran = transform_to_mat(transform)

    # print('tran', tran)
    # print('tran_inverse', np.linalg.inv(tran))

    orig = np.array([[point['x']],
                    [point['y']],
                    [point['z']],
                    [1]])

    new = tran.dot(orig)

    # print('pt', point)

    new = [
        new[0][0],
        new[1][0],
        new[2][0]
    ]
        # print('new', new)

    return new
