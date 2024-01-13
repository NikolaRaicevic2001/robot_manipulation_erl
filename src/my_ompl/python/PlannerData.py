#!/usr/bin/env python

try: 
   import graph_tool.all as gt
   graphtool = True
except ImportError:
   print('Failed to import graph-tool.  PlannerData will not be analyzed or plotted')
   graphtool = False

try:
   from ompl import base as ob
   from ompl import geometric as og
except ImportError:
   from os.path import abspath, dirname, join
   import sys
   sys.path.insert(0, '/home/erl-tianyu/Nikola_ws/ros2_ws/src/ompl-1.6.0/py-bindings')
   from ompl import base as ob
   from ompl import geometric as og

# Create a narrow passage between y=[-3,3].  Only a 6x6x6 cube will be valid, centered at origin
def isStateValid(state):
   if state.getY() >= -3 and state.getY() <= 3:
       return state.getX() >= -3 and state.getX() <= 3 and \
           state.getZ() >= -3 and state.getZ() <= 3
   return True

def useGraphTool(pd):
   # Extract the graphml representation of the planner data
   graphml = pd.printGraphML()
   f = open("graph.graphml", 'w')
   f.write(graphml)
   f.close()

   # Load the graphml data using graph-tool
   graph = gt.load_graph("graph.graphml", fmt="xml")
   edgeweights = graph.edge_properties["weight"]

   # Write some interesting statistics
   avgdeg, stddevdeg = gt.vertex_average(graph, "total")
   avgwt, stddevwt = gt.edge_average(graph, edgeweights)

   print("---- PLANNER DATA STATISTICS ----")
   print(str(graph.num_vertices()) + " vertices and " + str(graph.num_edges()) + " edges")
   print("Average vertex degree (in+out) = " + str(avgdeg) + "  St. Dev = " + str(stddevdeg))
   print("Average edge weight = " + str(avgwt)  + "  St. Dev = " + str(stddevwt))

   _, hist = gt.label_components(graph)
   print("Strongly connected components: " + str(len(hist)))

   # Make the graph undirected (for weak components, and a simpler drawing)
   graph.set_directed(False)
   _, hist = gt.label_components(graph)
   print("Weakly connected components: " + str(len(hist)))

   # Plotting the graph
   gt.remove_parallel_edges(graph) # Removing any superfluous edges

   edgeweights = graph.edge_properties["weight"]
   colorprops = graph.new_vertex_property("string")
   vertexsize = graph.new_vertex_property("double")

   start = -1
   goal = -1

   for v in range(graph.num_vertices()):

       # Color and size vertices by type: start, goal, other
       if pd.isStartVertex(v):
           start = v
           colorprops[graph.vertex(v)] = "cyan"
           vertexsize[graph.vertex(v)] = 10
       elif pd.isGoalVertex(v):
           goal = v
           colorprops[graph.vertex(v)] = "green"
           vertexsize[graph.vertex(v)] = 10
       else:
           colorprops[graph.vertex(v)] = "yellow"
           vertexsize[graph.vertex(v)] = 5

   # default edge color is black with size 0.5:


# Author: Ryan Luna

   edgecolor = graph.new_edge_property("string")
   edgesize = graph.new_edge_property("double")
   for e in graph.edges():
       edgecolor[e] = "black"
       edgesize[e] = 0.5

   # using A* to find shortest path in planner data
   if start != -1 and goal != -1:
       _, pred = gt.astar_search(graph, graph.vertex(start), edgeweights)

       # Color edges along shortest path red with size 3.0
       v = graph.vertex(goal)
       while v != graph.vertex(start):
           p = graph.vertex(pred[v])
           for e in p.out_edges():
               if e.target() == v:
                   edgecolor[e] = "red"
                   edgesize[e] = 2.0
           v = p

   # Writing graph to file:
   # pos indicates the desired vertex positions, and pin=True says that we
   # really REALLY want the vertices at those positions
   gt.graph_draw(graph, vertex_size=vertexsize, vertex_fill_color=colorprops,
                 edge_pen_width=edgesize, edge_color=edgecolor,
                 output="graph.png")
   print('\nGraph written to graph.png')

def plan():
   # construct the state space we are planning in
   space = ob.SE3StateSpace()


# Author: Ryan Luna


   # set the bounds for R^3 portion of SE(3)
   bounds = ob.RealVectorBounds(3)
   bounds.setLow(-10)
   bounds.setHigh(10)
   space.setBounds(bounds)

   # define a simple setup class
   ss = og.SimpleSetup(space)

   # create a start state
   start = ob.State(space)
   start().setX(-9)
   start().setY(-9)
   start().setZ(-9)
   start().rotation().setIdentity()

   # create a goal state
   goal = ob.State(space)
   goal().setX(-9)
   goal().setY(9)
   goal().setZ(-9)
   goal().rotation().setIdentity()

   ss.setStateValidityChecker(ob.StateValidityCheckerFn(isStateValid))

   # set the start and goal states
   ss.setStartAndGoalStates(start, goal, 0.05)

   # Lets use PRM.  It will have interesting PlannerData
   planner = og.PRM(ss.getSpaceInformation())
   ss.setPlanner(planner)
   ss.setup()

   # attempt to solve the problem
   solved = ss.solve(20.0)

   if solved:
       # print the path to screen
       print("Found solution:\n%s" % ss.getSolutionPath())

       # Extracting planner data from most recent solve attempt
       pd = ob.PlannerData(ss.getSpaceInformation())
       ss.getPlannerData(pd)

       # Computing weights of all edges based on state space distance
       pd.computeEdgeWeights()

       if graphtool:
           useGraphTool(pd)

if __name__ == "__main__":
   plan()
