import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from operator import itemgetter
import random
from collections import defaultdict

# 所有节点的邻接矩阵，并以稀疏矩阵的形式返回
def data_masks(all_sessions, n_node, hoplimit):
    adj = dict()
    for sess in all_sessions:
        for i, item in enumerate(sess):
            if i == len(sess)-1:
                break
            else:
                for j in range(max(0, i-hoplimit), min(i+hoplimit+1, len(sess))):
                    distance = abs(j - i)  # 计算距离
                    weight = 1 / (distance + 1)  # 根据距离计算权重
                    if sess[i] - 1 not in adj.keys():
                        adj[sess[i]-1] = dict()
                        adj[sess[i]-1][sess[i]-1] = 1
                        adj[sess[i]-1][sess[j]-1] = weight  # 使用权重替代固定值1
                    else:
                        if sess[j]-1 not in adj[sess[i]-1].keys():
                            adj[sess[i] - 1][sess[j] - 1] = weight  # 使用权重替代固定值1
                        else:
                            adj[sess[i]-1][sess[j]-1] += weight  # 使用权重替代固定值1
    row, col, data = [], [], []
    for i in adj.keys():
        item = adj[i]
        for j in item.keys():
            row.append(i)
            col.append(j)
            data.append(adj[i][j])
    coo = coo_matrix((data, (row, col)), shape=(n_node, n_node))
    return coo

class Data():
    def __init__(self, data, all_train, hoplimit, shuffle=False, n_node=None):
        self.raw = np.asarray(data[0], dtype=object)
        adj = data_masks(all_train, n_node, hoplimit)
        # # print(adj.sum(axis=0))
        self.adjacency = adj.multiply(1.0/adj.sum(axis=0).reshape(1, -1))
        self.n_node = n_node
        self.targets = np.asarray(data[1])
        self.length = len(self.raw)
        self.shuffle = shuffle

    def get_overlap(self, sessions):
        matrix = np.zeros((len(sessions), len(sessions)))
        for i in range(len(sessions)):
            seq_a = set(sessions[i])
            seq_a.discard(0)
            for j in range(i+1, len(sessions)):
                seq_b = set(sessions[j])
                seq_b.discard(0)
                overlap = seq_a.intersection(seq_b)
                ab_set = seq_a | seq_b
                matrix[i][j] = float(len(overlap))/float(len(ab_set))
                matrix[j][i] = matrix[i][j]
        # matrix = self.dropout(matrix, 0.2)
        matrix = matrix + np.diag([1.0]*len(sessions))
        degree = np.sum(np.array(matrix), 1)
        degree = np.diag(1.0/degree)
        return matrix, degree

    def generate_batch(self, batch_size):
        if self.shuffle:
            shuffled_arg = np.arange(self.length)
            np.random.shuffle(shuffled_arg)
            self.raw = self.raw[shuffled_arg]
            self.targets = self.targets[shuffled_arg]
        n_batch = int(self.length / batch_size)
        if self.length % batch_size != 0:
            n_batch += 1
        slices = np.split(np.arange(n_batch * batch_size), n_batch)
        slices[-1] = np.arange(self.length-batch_size, self.length)
        return slices

    def get_slice(self, index):
        items, num_node = [], []
        inp = self.raw[index]
        for session in inp:
            num_node.append(len(np.nonzero(session)[0]))
        max_n_node = np.max(num_node)
        session_len = []
        reversed_sess_item = []
        mask = []
        # item_set = set()
        for session in inp:
            nonzero_elems = np.nonzero(session)[0]
            # item_set.update(set([t-1 for t in session]))
            session_len.append([len(nonzero_elems)])
            items.append(session + (max_n_node - len(nonzero_elems)) * [0])
            mask.append([1]*len(nonzero_elems) + (max_n_node - len(nonzero_elems)) * [0])
            reversed_sess_item.append(list(reversed(session)) + (max_n_node - len(nonzero_elems)) * [0])
        # item_set = list(item_set)
        # index_list = [item_set.index(a) for a in self.targets[index]-1]
        diff_mask = np.ones(shape=[100, self.n_node]) * (1/(self.n_node - 1))
        for count, value in enumerate(self.targets[index]-1):
            diff_mask[count][value] = 1
        return self.targets[index]-1, session_len,items, reversed_sess_item, mask, diff_mask
