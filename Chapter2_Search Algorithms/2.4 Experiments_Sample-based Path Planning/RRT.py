import copy
import math
import random
import time
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation as Rot
import numpy as np
import os

show_animation = True


class RRT:
    def __init__(self, obstacleList, randArea, expandDis=2.0, goalSampleRate=10, maxIter=200):
        self.start = None
        self.goal = None
        self.min_rand = randArea[0]
        self.max_rand = randArea[1]
        self.expand_dis = expandDis
        self.goal_sample_rate = goalSampleRate
        self.max_iter = maxIter
        self.obstacle_list = obstacleList
        self.node_list = None
        self.num = 0

    def rrt_planning(self, start, goal, animation=True):
        start_time = time.time()
        self.start = Node(start[0], start[1])
        self.goal = Node(goal[0], goal[1])
        self.node_list = [self.start]
        path = None
        for i in range(self.max_iter):
            rnd = self.sample()
            n_ind = self.get_nearest_list_index(self.node_list, rnd)
            nearestNode = self.node_list[n_ind]
            # steer
            theta = math.atan2(rnd[1] - nearestNode.y, rnd[0] - nearestNode.x)
            newNode = self.get_new_node(theta, n_ind, nearestNode)
            noCollision = self.check_segment_collision(newNode.x, newNode.y, nearestNode.x, nearestNode.y)
            if noCollision:
                self.node_list.append(newNode)
                if animation:
                    self.draw_graph(newNode, path)
                if self.is_near_goal(newNode):
                    if self.check_segment_collision(newNode.x, newNode.y, self.goal.x, self.goal.y):
                        lastIndex = len(self.node_list) - 1
                        path = self.get_final_course(lastIndex)
                        pathLen = self.get_path_len(path)
                        print("current path length: {}, It costs {} s".format(pathLen, time.time() - start_time))
                        if animation:
                            self.draw_graph(newNode, path)
                        return path

    def rrt_star_planning(self, start, goal, animation=True):
        start_time = time.time()
        self.start = Node(start[0], start[1])
        self.goal = Node(goal[0], goal[1])
        self.node_list = [self.start]
        path = None
        lastPathLength = float('inf')
        for i in range(self.max_iter):
            rnd = self.sample()
            n_ind = self.get_nearest_list_index(self.node_list, rnd)
            nearestNode = self.node_list[n_ind]
            # steer
            theta = math.atan2(rnd[1] - nearestNode.y, rnd[0] - nearestNode.x)
            newNode = self.get_new_node(theta, n_ind, nearestNode)
            noCollision = self.check_segment_collision(newNode.x, newNode.y, nearestNode.x, nearestNode.y)
            if noCollision:
                nearInds = self.find_near_nodes(newNode)
                newNode = self.choose_parent(newNode, nearInds)
                self.node_list.append(newNode)
                self.rewire(newNode, nearInds)
                if animation:
                    self.draw_graph(newNode, path)
                if self.is_near_goal(newNode):
                    if self.check_segment_collision(newNode.x, newNode.y, self.goal.x, self.goal.y):
                        lastIndex = len(self.node_list) - 1
                        tempPath = self.get_final_course(lastIndex)
                        tempPathLen = self.get_path_len(tempPath)
                        if lastPathLength > tempPathLen:
                            path = tempPath
                            lastPathLength = tempPathLen
                            print(
                                "current path length: {}, It costs {} s".format(tempPathLen, time.time() - start_time))
        return path

    def informed_rrt_star_planning(self, start, goal, animation=True):
        start_time = time.time()
        self.start = Node(start[0], start[1])
        self.goal = Node(goal[0], goal[1])
        self.node_list = [self.start]
        # max length we expect to find in our 'informed' sample space,
        # starts as infinite
        cBest = float('inf')
        path = None
        # Computing the sampling space
        cMin = math.sqrt(pow(self.start.x - self.goal.x, 2)
                         + pow(self.start.y - self.goal.y, 2))
        xCenter = np.array([[(self.start.x + self.goal.x) / 2.0], [(self.start.y + self.goal.y) / 2.0], [0]])
        a1 = np.array([[(self.goal.x - self.start.x) / cMin],
                       [(self.goal.y - self.start.y) / cMin], [0]])
        e_theta = math.atan2(a1[1], a1[0])
        # 直接用二维平面上的公式（2选1）
        C = np.array([[math.cos(e_theta), -math.sin(e_theta), 0], [math.sin(e_theta), math.cos(e_theta), 0], [0, 0, 1]])
        for i in range(self.max_iter):
            rnd = self.informed_sample(cBest, cMin, xCenter, C)
            n_ind = self.get_nearest_list_index(self.node_list, rnd)
            nearestNode = self.node_list[n_ind]
            theta = math.atan2(rnd[1] - nearestNode.y, rnd[0] - nearestNode.x)
            newNode = self.get_new_node(theta, n_ind, nearestNode)
            noCollision = self.check_segment_collision(newNode.x, newNode.y, nearestNode.x, nearestNode.y)
            if noCollision:
                nearInds = self.find_near_nodes(newNode)
                newNode = self.choose_parent(newNode, nearInds)
                self.node_list.append(newNode)
                self.rewire(newNode, nearInds)
                if self.is_near_goal(newNode):
                    if self.check_segment_collision(newNode.x, newNode.y, self.goal.x, self.goal.y):
                        lastIndex = len(self.node_list) - 1
                        tempPath = self.get_final_course(lastIndex)
                        tempPathLen = self.get_path_len(tempPath)
                        if tempPathLen < cBest:
                            path = tempPath
                            cBest = tempPathLen
                            print(
                                "current path length: {}, It costs {} s".format(tempPathLen, time.time() - start_time))
            if animation:
                self.draw_graph_informed_RRTStar(xCenter=xCenter, cBest=cBest, cMin=cMin, e_theta=e_theta, rnd=rnd,
                                                 path=path)
                return path

    def sample(self):
        if random.randint(0, 100) > self.goal_sample_rate:
            rnd = [random.uniform(self.min_rand, self.max_rand), random.uniform(self.min_rand, self.max_rand)]
        else:  # goal point sampling
            rnd = [self.goal.x, self.goal.y]
        return rnd

    def choose_parent(self, newNode, nearInds):
        if len(nearInds) == 0:
            return newNode
        dList = []
        for i in nearInds:
            dx = newNode.x - self.node_list[i].x
            dy = newNode.y - self.node_list[i].y
            d = math.hypot(dx, dy)
            theta = math.atan2(dy, dx)
            if self.check_collision(self.node_list[i], theta, d):
                dList.append(self.node_list[i].cost + d)
            else:
                dList.append(float('inf'))
        minCost = min(dList)
        minInd = nearInds[dList.index(minCost)]
        if minCost == float('inf'):
            print("min cost is inf")
            return newNode
        newNode.cost = minCost
        newNode.parent = minInd
        return newNode

    def find_near_nodes(self, newNode):
        n_node = len(self.node_list)
        r = 50.0 * math.sqrt((math.log(n_node) / n_node))
        d_list = [(node.x - newNode.x) ** 2 + (node.y - newNode.y) ** 2 for node in self.node_list]
        near_inds = [d_list.index(i) for i in d_list if i <= r ** 2]
        return near_inds

    def informed_sample(self, cMax, cMin, xCenter, C):
        if cMax < float('inf'):
            r = [cMax / 2.0, math.sqrt(cMax ** 2 - cMin ** 2) / 2.0, math.sqrt(cMax ** 2 - cMin ** 2) / 2.0]
            L = np.diag(r)
            xBall = self.sample_unit_ball()
            rnd = np.dot(np.dot(C, L), xBall) + xCenter
            rnd = [rnd[(0, 0)], rnd[(1, 0)]]
        else:
            rnd = self.sample()
        return rnd

    @staticmethod
    def sample_unit_ball():
        a = random.random()
        b = random.random()
        if b < a:
            a, b = b, a
        sample = (b * math.cos(2 * math.pi * a / b), b * math.sin(2 * math.pi * a / b))
        return np.array([[sample[0]], [sample[1]], [0]])

    @staticmethod
    def get_path_len(path):
        pathLen = 0
        for i in range(1, len(path)):
            node1_x = path[i][0]
            node1_y = path[i][1]
            node2_x = path[i - 1][0]
            node2_y = path[i - 1][1]
            pathLen += math.sqrt((node1_x - node2_x)
                                 ** 2 + (node1_y - node2_y) ** 2)
        return pathLen

    @staticmethod
    def line_cost(node1, node2):
        return math.sqrt((node1.x - node2.x) ** 2 + (node1.y - node2.y) ** 2)

    @staticmethod
    def get_nearest_list_index(nodes, rnd):
        dList = [(node.x - rnd[0]) ** 2 + (node.y - rnd[1]) ** 2 for node in nodes]
        minIndex = dList.index(min(dList))
        return minIndex

    def get_new_node(self, theta, n_ind, nearestNode):
        newNode = copy.deepcopy(nearestNode)
        newNode.x += self.expand_dis * math.cos(theta)
        newNode.y += self.expand_dis * math.sin(theta)
        newNode.cost += self.expand_dis
        newNode.parent = n_ind
        return newNode

    def is_near_goal(self, node):
        d = self.line_cost(node, self.goal)
        if d < self.expand_dis:
            return True
        return False

    def rewire(self, newNode, nearInds):
        n_node = len(self.node_list)
        for i in nearInds:
            nearNode = self.node_list[i]
            d = math.sqrt((nearNode.x - newNode.x) ** 2 + (nearNode.y - newNode.y) ** 2)
            s_cost = newNode.cost + d
            if nearNode.cost > s_cost:
                theta = math.atan2(newNode.y - nearNode.y, newNode.x - nearNode.x)
                if self.check_collision(nearNode, theta, d):
                    nearNode.parent = n_node - 1
                    nearNode.cost = s_cost

    @staticmethod
    def distance_squared_point_to_segment(v, w, p):
        # Return minimum distance between line segment vw and point p
        if np.array_equal(v, w):
            return (p - v).dot(p - v)  # v == w case
        l2 = (w - v).dot(w - v)  # i.e. |w-v|^2 -  avoid a sqrt
        t = max(0, min(1, (p - v).dot(w - v) / l2))
        projection = v + t * (w - v)  # Projection falls on the segment
        return (p - projection).dot(p - projection)

    def check_segment_collision(self, x1, y1, x2, y2):
        for (ox, oy, size) in self.obstacle_list:
            dd = self.distance_squared_point_to_segment(np.array([x1, y1]), np.array([x2, y2]), np.array([ox, oy]))
            if dd <= size ** 2:
                return False  # collision
        return True

    def check_collision(self, nearNode, theta, d):
        tmpNode = copy.deepcopy(nearNode)
        end_x = tmpNode.x + math.cos(theta) * d
        end_y = tmpNode.y + math.sin(theta) * d
        return self.check_segment_collision(tmpNode.x, tmpNode.y, end_x, end_y)

    def get_final_course(self, lastIndex):
        path = [[self.goal.x, self.goal.y]]
        while self.node_list[lastIndex].parent is not None:
            node = self.node_list[lastIndex]
            path.append([node.x, node.y])
            lastIndex = node.parent
        path.append([self.start.x, self.start.y])
        return path

    def draw_graph_informed_RRTStar(self, xCenter=None, cBest=None, cMin=None, e_theta=None, rnd=None, path=None):
        plt.clf()
        # for stopping simulation with the esc key.
        plt.gcf().canvas.mpl_connect(
            'key_release_event',
            lambda event: [exit(0) if event.key == 'escape' else None])
        if rnd is not None:
            plt.plot(rnd[0], rnd[1], "^k")
            if cBest != float('inf'):
                self.plot_ellipse(xCenter, cBest, cMin, e_theta)
        for node in self.node_list:
            if node.parent is not None:
                if node.x or node.y is not None:
                    plt.plot([node.x, self.node_list[node.parent].x], [
                        node.y, self.node_list[node.parent].y], "-g")
        for (ox, oy, size) in self.obstacle_list:
            plt.plot(ox, oy, "ok", ms=30 * size)
        if path is not None:
            plt.plot([x for (x, y) in path], [y for (x, y) in path], '-r')
        plt.plot(self.start.x, self.start.y, "xr")
        plt.plot(self.goal.x, self.goal.y, "xr")
        plt.axis([-2, 18, -2, 15])
        plt.grid(True)
        plt.pause(0.01)

    @staticmethod
    def plot_ellipse(xCenter, cBest, cMin, e_theta):  # pragma: no cover
        a = math.sqrt(cBest ** 2 - cMin ** 2) / 2.0
        b = cBest / 2.0
        angle = math.pi / 2.0 - e_theta
        cx = xCenter[0]
        cy = xCenter[1]
        t = np.arange(0, 2 * math.pi + 0.1, 0.1)
        x = [a * math.cos(it) for it in t]
        y = [b * math.sin(it) for it in t]
        rot = Rot.from_euler('z', -angle).as_matrix()[0:2, 0:2]
        fx = rot @ np.array([x, y])
        px = np.array(fx[0, :] + cx).flatten()
        py = np.array(fx[1, :] + cy).flatten()
        plt.plot(cx, cy, "xc")
        plt.plot(px, py, "--c")

    def draw_graph(self, rnd=None, path=None, num=None):
        num = self.num
        plt.clf()
        # for stopping simulation with the esc key.
        plt.gcf().canvas.mpl_connect(
            'key_release_event',
            lambda event: [exit(0) if event.key == 'escape' else None])
        if rnd is not None:
            plt.plot(rnd.x, rnd.y, "^k")
        for node in self.node_list:
            if node.parent is not None:
                if node.x or node.y is not None:
                    plt.plot([node.x, self.node_list[node.parent].x], [node.y, self.node_list[node.parent].y], "-g")
        for (ox, oy, size) in self.obstacle_list:
            plt.plot(ox, oy, "ok", ms=30 * size)
        plt.plot(self.start.x, self.start.y, "xr")
        plt.plot(self.goal.x, self.goal.y, "xr")
        if path is not None:
            plt.plot([x for (x, y) in path], [y for (x, y) in path], '-r')
        plt.axis([-2, 18, -2, 15])
        plt.grid(True)
        num = num + 1
        self.num = num
        plt.savefig(format(str(num)) + '.svg', dpi=600, format='svg')
        plt.pause(0.01)


class Node:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.cost = 0.0
        self.parent = None


def main():
    print("Start rrt planning")
    obstacleList = [(3, 3, 1.5), (12, 2, 3), (3, 9, 2), (9, 11, 2), ]
    rrt = RRT(randArea=[-2, 18], obstacleList=obstacleList, maxIter=200)
    path = rrt.rrt_planning(start=[0, 0], goal=[15, 12], animation=show_animation)
    print("Done!!")
    if show_animation and path:
        plt.show()


if __name__ == '__main__':
    main()
