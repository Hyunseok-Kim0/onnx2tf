import random
random.seed(0)
import numpy as np
np.random.seed(0)
import tensorflow as tf
import onnx_graphsurgeon as gs
from utils.common_functions import get_constant_or_variable


def make_node(
    *,
    graph_node: gs.Node,
    tf_layers_dict: dict,
    **kwargs: dict,
):
    """Gemm

    Parameters
    ----------
    graph_node: gs.Node
        graph_surgeon Node

    tf_layers_dict: dict
        optype, shape, dtype, tensorflow graph
    """
    graph_node_input_1 = get_constant_or_variable(graph_node.inputs[0])
    graph_node_input_2 = get_constant_or_variable(graph_node.inputs[1])
    if len(graph_node.inputs) > 2:
        graph_node_input_3 = get_constant_or_variable(graph_node.inputs[2])
    else:
        graph_node_input_3 = 0
    graph_node_output: gs.Variable = graph_node.outputs[0]

    input_tensor_x = tf_layers_dict[graph_node_input_1.name]['tf_node'] \
        if isinstance(graph_node_input_1, gs.Variable) else graph_node_input_1
    input_tensor_y = tf_layers_dict[graph_node_input_2.name]['tf_node'] \
        if isinstance(graph_node_input_2, gs.Variable) else graph_node_input_2
    input_tensor_z = tf_layers_dict[graph_node_input_3.name]['tf_node'] \
        if isinstance(graph_node_input_3, gs.Variable) else graph_node_input_3
    input_tensor_x_dtype = input_tensor_x.dtype
    input_tensor_x = tf.keras.layers.Flatten()(input_tensor_x)
    # The Flatten API changes data type from tf.float64 to tf.float32
    # so we need the following line to get the original type back
    input_tensor_x = tf.cast(input_tensor_x, input_tensor_x_dtype) \
        if input_tensor_x_dtype is tf.float64 else input_tensor_x

    shape = graph_node_output.shape
    dtype = graph_node_output.dtype

    if bool(graph_node.attrs.get('transA', 0)):
        x = tf.transpose(x)
    if bool(graph_node.attrs.get('transB', 0)):
        y = tf.transpose(y)
    alpha = graph_node.attrs.get('alpha', 1.0)
    beta = graph_node.attrs.get('beta', 1.0)

    # Preserving Graph Structure (Dict)
    tf_layers_dict[graph_node_output.name] = {
        'optype': graph_node.op,
        'shape': shape,
        'dtype': dtype,
    }

    # Generation of TF OP
    # We cast to either input or attribute data type to preserve precision
    if input_tensor_x_dtype in [tf.float64]:
        # cast to input data type
        alpha = tf.cast(alpha, input_tensor_x_dtype)
        beta = tf.cast(beta, input_tensor_x_dtype)
        tf_layers_dict[graph_node_output.name]['tf_node'] = \
            alpha * tf.matmul(x, y) + beta * z
    else:
        # cast to attribute data type
        x = tf.cast(x, tf.float32)
        y = tf.cast(y, tf.float32)
        z = tf.cast(z, tf.float32)
        result = alpha * tf.matmul(x, y) + beta * z
        tf_layers_dict[graph_node_output.name]['tf_node'] = \
            tf.cast(result, input_tensor_x_dtype)