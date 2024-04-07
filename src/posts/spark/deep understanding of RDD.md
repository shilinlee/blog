---
title: "Spark系列: 深入理解RDD"
icon: pen-to-square
date: 2019-01-28
category:
  - 大数据
tag:
  - spark
  - 入门
  - RDD
---

## RDD介绍

[RDD参考论文](http://people.csail.mit.edu/matei/papers/2012/nsdi_spark.pdf)

RDD的全称是：Resilient Distributed Dataset （弹性分布式数据集），它有几个关键的特性：

- RDD是只读的，表示它的不可变性。
- 可以并行的操作分区集合上的所有元素。
- 天生具有容错机制的特殊集。
- 只能通过在稳定的存储器或其他RDD上的确定性操作（转换）来创建。

每一种RDD类型都包含以下五种特性：

- A list of partitions
*  A function for computing each split
*  A list of dependencies on other RDDs
*  Optionally, a Partitioner for key-value RDDs (e.g. to say that the RDD is hash-partitioned)
*  Optionally, a list of preferred locations to compute each split on (e.g. block locations for an HDFS file)

为解决资源不能在内存中，并且跨集群重复使用的问题，我们抽象出了RDD的概念，可以支持在大量的应用之间高效的重复利用数据。RDD是一种具备容错性、并行的数据结构，可以在内存中持久化，以便在大量的算子之间操作。

## Resilient Distributed Datasets (RDDs)

### RDD的抽象

- 只读的分区记录的集合
- RDD只能基于在稳定物理存储中的数据集和其他已有的RDD上执行确定性操作来创建，RDD含有如何从其他RDD衍生（即计算）出本RDD的相关信息（即Lineage），据此可以从物理存储的数据计算出相应的RDD分区
- 用户可控制RDDs的两个方面：持久化和分区性

### Spark编程接口

在Spark中，RDD被表示为对象，通过这些对象上的方法（或函数）调用转换。

定义RDD之后，程序员就可以在动作中使用RDD了。动作是向应用程序返回值，或向存储系统导出数据的那些操作，例如，count（返回RDD中的元素个数），collect（返回元素本身），save（将RDD输出到存储系统）。在Spark中，只有在动作第一次使用RDD时，才会计算RDD（即延迟计算）。这样在构建RDD的时候，运行时通过管道的方式传输多个转换。

程序员还可以从两个方面控制RDD，即缓存和分区。用户可以请求将RDD缓存，这样运行时将已经计算好的RDD分区存储起来，以加速后期的重用。缓存的RDD一般存储在内存中，但如果内存不够，可以写到磁盘上。

另一方面，RDD还允许用户根据关键字（key）指定分区顺序，这是一个可选的功能。目前支持哈希分区和范围分区。例如，应用程序请求将两个RDD按照同样的哈希分区方式进行分区（将同一机器上具有相同关键字的记录放在一个分区），以加速它们之间的join操作。

### 控制台日志挖掘

```
lines = spark.textFile("hdfs://...")

errors = lines.filter(_.startsWith("ERROR"))

errors.cache()

// Count errors mentioning MySQL:
errors.filter(_.contains("MySQL")).count()
// Return the time fields of errors mentioning
// HDFS as an array (assuming time is field
// number 3 in a tab-separated format):
errors.filter(_.contains("HDFS")).map(_.split(’\t’)(3)).collect()
```

![image](https://user-images.githubusercontent.com/22270117/60391725-08ca8d00-9b28-11e9-87a2-bacef30bb79d.png)

为了说明模型的容错性，给出了3个查询的Lineage图。Spark调度器以流水线的方式执行后两个转换，向拥有errors分区缓存的节点发送一组任务。此外，如果某个errors分区丢失，Spark只在相应的lines分区上执行filter操作来重建该errors分区。

### RDD与分布式共享内存

![image](https://user-images.githubusercontent.com/22270117/60391756-8b534c80-9b28-11e9-8f9d-6572a1e87f57.png)

注意，通过备份任务的拷贝，RDD还可以处理落后任务（即运行很慢的节点），这点与MapReduce[12]类似。而DSM则难以实现备份任务，因为任务及其副本都需要读写同一个内存位置。

与DSM相比，RDD模型有两个好处:

- 对于RDD中的批量操作，运行时将根据数据存放的位置来调度任务，从而提高性能。（计算向数据靠拢）
- 对于基于扫描的操作，如果内存不足以缓存整个RDD，就进行部分缓存。把内存放不下的分区存储到磁盘上，此时性能与现有的数据流系统差不多。

最后看一下读操作的粒度。RDD上的很多动作（如count和collect）都是批量读操作，即扫描整个数据集，可以将任务分配到距离数据最近的节点上。同时，RDD也支持细粒度操作，即在哈希或范围分区的RDD上执行关键字查找。

## RDD模型的优势

### Spark中的RDD操作

下面是Spark中的RDD转换和动作。每个操作都给出了标识，其中方括号表示类型参数。前面说过转换是延迟操作，用于定义新的RDD；而动作启动计算操作，并向用户程序返回值或向外部存储写数据。

![image](https://user-images.githubusercontent.com/22270117/60391830-403a3900-9b2a-11e9-9895-3115ee11f917.png)

### 应用程序示例

#### 逻辑回归（Logistic Regression）

例如下面的程序是逻辑回归的实现。逻辑回归是一种常见的分类算法，即寻找一个最佳分割两组点（即垃圾邮件和非垃圾邮件）的超平面w。算法采用梯度下降的方法：开始时w为随机值，在每一次迭代的过程中，对w的函数求和，然后朝着优化的方向移动w。

```
val points = spark.textFile(...).map(parsePoint).persist()
var w = // random initial vector
for (i <- 1 to ITERATIONS) { 
	val gradient = points.map{ 
			p =>p.x * (1/(1+exp(-p.y*(w dot p.x)))-1)*p.y
		}.reduce((a,b) => a+b)
	w -= gradient
}
```

首先定义一个名为points的缓存RDD，这是在文本文件上执行map转换之后得到的，即将每个文本行解析为一个Point对象。然后在points上反复执行map和reduce操作，每次迭代时通过对当前w的函数进行求和来计算梯度。

#### PageRank

该算法通过合计链接到自身页面的page对其的贡献，进而迭代式地更新自身的排名。每一次的迭代中，每一个文件（page）都将r/m的贡献发送给他的邻居，其中r是它的rank，n是它邻居页面的的数目，之后，它会将自身的排名更新为α/N + (1 − α)∑ci，其中 ∑ci是是当前页面获取到的贡献的总和，N是文件（page）的总数

![image](https://user-images.githubusercontent.com/22270117/60391942-8f816900-9b2c-11e9-80b7-2e971256831d.png)

## RDD的描述

我们希望在不修改调度器的前提下，支持RDD上的各种转换操作，同时能够从这些转换获取Lineage信息。为此，我们为RDD设计了一组小型通用的内部接口。

简单地说，每个RDD都包含（**RDD的内部实现接口**）：

| Operation                | Meaning                                                      |
| ------------------------ | ------------------------------------------------------------ |
| partitions()             | Return a list of Partition objects                           |
| preferredLocations(p)    | List nodes where partition p can be accessed faster due to data locality |
| dependencies()           | Return a list of dependencies                                |
| iterator(p, parentIters) | Compute the elements of partition pgiven iterators for its parent partitions |
| partitioner()            | Return metadata specifying whether the RDD is hash/range partitioned |

设计接口的一个关键问题就是，如何表示RDD之间的依赖。我们发现RDD之间的依赖关系可以分为两类，即：

- 窄依赖（narrow dependencies）：子RDD的每个分区依赖于常数个父分区（即与数据规模无关）；
- 宽依赖（wide dependencies）：子RDD的每个分区依赖于所有父RDD分区。例如，map产生窄依赖，而join则是宽依赖（除非父RDD被哈希分区）。

![image](https://user-images.githubusercontent.com/22270117/60392035-1e42b580-9b2e-11e9-8040-f5d7d23f19ee.png)

区分这两种依赖很有用。

- **窄依赖**允许在一个集群节点上以流水线的方式（pipeline）计算所有父分区。例如，逐个元素地执行map、然后filter操作；
- **宽依赖**则需要首先计算好所有父分区数据，然后在节点之间进行Shuffle，这与MapReduce类似。
- **窄依赖**能够更有效地进行失效节点的恢复，即只需重新计算丢失RDD分区的父分区，而且不同节点之间可以并行计算；
- 对于一个**宽依赖**关系的Lineage图，单个节点失效可能导致这个RDD的所有祖先丢失部分分区，因而需要整体重新计算。

### Spark任务调度器

调度器根据RDD的结构信息为每个动作确定有效的执行计划。调度器的接口是`runJob`函数，参数为RDD及其分区集，和一个RDD分区上的函数。该接口足以表示Spark中的所有动作（即count、collect、save等）。

总的来说，我们的调度器跟Dryad类似，但我们还考虑了哪些RDD分区是缓存在内存中的。**调度器根据目标RDD的Lineage图创建一个由stage构成的无回路有向图（DAG）**。**每个stage内部尽可能多地包含一组具有窄依赖关系的转换，并将它们流水线并行化（pipeline）**。

**stage的边界有两种情况**：

- 宽依赖上的Shuffle操作；
- 已缓存分区，它可以缩短父RDD的计算过程。

父RDD完成计算后，可以在stage内启动一组任务计算丢失的分区。

![image](https://user-images.githubusercontent.com/22270117/60392092-0d467400-9b2f-11e9-90af-b280763147ed.png)

### 支持检查点（Checkpointing）

尽管RDD中的Lineage信息可以用来故障恢复，但对于那些Lineage链较长的RDD来说，这种恢复可能很耗时。如果将Lineage链存到物理存储中，再定期对RDD执行检查点操作就很有效。

一般来说，Lineage链较长、宽依赖的RDD需要采用检查点机制。这种情况下，集群的节点故障可能导致每个父RDD的数据块丢失，因此需要全部重新计算。将窄依赖的RDD数据存到物理存储中可以实现优化，将数据点和不变的顶点状态存储起来，就不再需要检查点操作。

当前Spark版本提供检查点API，但由用户决定是否需要执行检查点操作。今后我们将实现自动检查点，根据成本效益分析确定RDD Lineage图中的最佳检查点位置。

值得注意的是，因为RDD是只读的，所以不需要任何一致性维护（例如写复制策略，分布式快照或者程序暂停等）带来的开销，后台执行检查点操作。

### 缓存管理

Worker节点将RDD分区以Java对象的形式缓存在内存中。由于大部分操作是基于扫描的，采取RDD级的LRU（最近最少使用）替换策略（即不会为了装载一个RDD分区而将同一RDD的其他分区替换出去）。

目前这种简单的策略适合大多数用户应用。另外，使用带参数的cache操作可以设定RDD的缓存优先级。

## 相关工作

**分布式共享内存（DSM）**。RDD可以看成是一个基于DSM研究得到的抽象。RDD提供了一个比DSM限制更严格的编程模型，并能在节点失效时高效地重建数据集。DSM通过检查点实现容错，而Spark使用Lineage重建RDD分区，这些分区可以在不同的节点上重新并行处理，而不需要将整个程序回退到检查点再重新运行。RDD能够像MapReduce一样将计算推向数据，并通过推测执行来解决某些任务计算进度落后的问题，推测执行在一般的DSM系统上是很难实现的。

**Lineage**。在科学计算和数据库领域，对于一些应用，如需要解释结果以及允许被重新生成、工作流中发现了bug或者数据集丢失需要重新处理数据，表示数据的Lineage和原始信息一直以来都是一个研究课题。RDD提供了一个受限的编程模型，在这个模型中使用细粒度的Lineage来表示是非常容易的，因此它可以被用于容错。