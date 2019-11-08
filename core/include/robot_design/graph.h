#pragma once

#include <cmath>
#include <Eigen/Dense>
#include <memory>
#include <ostream>
#include <robot_design/robot.h>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace robot_design {

using SubgraphIndex = std::size_t;
using NodeIndex = std::size_t;
using EdgeIndex = std::size_t;

// Nodes contain Link attributes which should be shared across all instances
// See the definition of Link for more information about these attributes
struct NodeAttributes {
  std::string label_;
  JointType joint_type_;
  Vector3 joint_axis_;
  LinkShape shape_;
  Scalar length_;

  EIGEN_MAKE_ALIGNED_OPERATOR_NEW;
};

struct Node {
  std::string name_;
  NodeAttributes attrs_;
};

// Edges contain Link attributes which are unique to each instance
// E.g. the rigid transformation relative to the parent link, uniform scaling
struct EdgeAttributes {
  std::string id_;
  std::string label_;
  Scalar joint_pos_;
  Quaternion joint_rot_;
  Scalar scale_;

  EIGEN_MAKE_ALIGNED_OPERATOR_NEW;
};

struct Edge {
  NodeIndex head_;
  NodeIndex tail_;
  EdgeAttributes attrs_;
};

// Subgraphs are collections of nodes and edges with default attributes
// Nodes and edges may belong to multiple subgraphs
struct Subgraph {
  std::string name_;
  std::set<NodeIndex> nodes_;
  std::set<EdgeIndex> edges_;
  NodeAttributes node_attrs_;
  EdgeAttributes edge_attrs_;
};

struct Graph {
  std::string name_;
  std::vector<Node> nodes_;
  std::vector<Edge> edges_;
  std::vector<Subgraph> subgraphs_;
};

struct GraphMapping {
  // Node i in the domain graph maps to node_mapping_[i] in the codomain graph
  std::vector<NodeIndex> node_mapping_;
  // Edge l in the domain graph maps to edge_mapping_[l] in the codomain graph
  std::vector<std::vector<NodeIndex>> edge_mapping_;
};

struct Rule {
  Graph lhs_;
  Graph rhs_;
  Graph common_;
  GraphMapping common_to_lhs_;
  GraphMapping common_to_rhs_;
};

std::vector<Graph> loadGraphs(const std::string &filename);

void updateNodeAttributes(
    NodeAttributes &node_attrs,
    const std::vector<std::pair<std::string, std::string>> &attr_list);

void updateEdgeAttributes(
    EdgeAttributes &edge_attrs,
    const std::vector<std::pair<std::string, std::string>> &attr_list);

std::ostream &operator<<(std::ostream &out, const Node &node);

std::ostream &operator<<(std::ostream &out, const Edge &edge);

std::ostream &operator<<(std::ostream &out, const Graph &graph);

Robot buildRobot(const Graph &graph);

Rule createRuleFromGraph(const Graph &graph);

std::vector<GraphMapping> findMatches(
    const Graph &pattern, const Graph &target);

Graph applyRule(
    const Rule &rule, const Graph &target, const GraphMapping &lhs_to_target);

}  // namespace robot_design