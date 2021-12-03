# Reconstruction Dataset Statistics

## Design Complexity
A key goal of the reconstruction dataset is to provide a suitably scoped baseline for learning-based approaches to CAD reconstruction. Restricting the modeling operations to _sketch_ and _extrude_ vastly narrows the design space and enables simpler approaches for reconstruction. Each design represents a component in Fusion 360 that can have multiple geometric bodies. The vast majority of designs have a single body. 

![Body Count Per Design](https://i.gyazo.com/01db2404d160935e2020d88383ba51f8.png)

The number of B-Rep faces in each design gives a good indication of the complexity of the dataset. Below we show the number of faces per design as a distribution, with the peak being between 5-10 faces per design. As we do not filter any of the designs based on complexity, this distribution reflects real designs where simple washers and flat plates are common components in mechanical assemblies. 

![Face Count Per Design](https://i.gyazo.com/124d7bcb0a9760d00404bfeb2c1128d5.png)

## Construction Sequence
The construction sequence is the series of _sketch_ and _extrude_ operations that are executed to produce the final geometry. Each construction sequence must have at least one _sketch_ and one _extrude_ step, for a minimum of two steps. The average number of steps is 4.74, the median 4, the mode 2, and the maximum 61. Below we illustrate the distribution of construction sequence length.

![Construction Sequence Length](https://i.gyazo.com/db0be05dbe0c2abf64c45f8ddb40b41c.png)


The most frequent construction sequence combinations are shown below. S indicates a _sketch_ and E indicates an _extrude_ operation.

![Construction Sequence Frequency](https://i.gyazo.com/3c2353fb3ebdffb307c0981eb8358725.png)

## Sketch
### Curves
Each sketch is made up on different types of curves, such as lines, arcs, and circles. It is notable that mechanical CAD sketches rely heavily on lines, circles, and arcs rather than spline curves.
Below we show the overall distribution of different curve types in the reconstruction dataset.

![Curve Type Distribution](https://i.gyazo.com/f27035588f435e18a58a4ae5c1ce0bde.png)

The graph below illustrates the distribution of curve count per design, as another measure of design complexity.

![Curve Count Per Design](https://i.gyazo.com/437eccd587ef9892c851b3fb62eb40d2.png)

Below we show the frequency that different curve combinations are used together in a design. 
Each curve type is abbreviated as follows: 
- C: `SketchCircle`
- A: `SketchArc`
- L: `SketchLine`
- S: `SketchFittedSpline`

![Curve Type Combination Frequency](https://i.gyazo.com/893bed76b7e957aaea5f2b8f0f177cd5.png)

### Dimensions & Constraints
Shown below are the distribution of dimension and constraint types in the dataset. 

![Dimension Types](https://i.gyazo.com/44298f03a6028a61d0937f9aa6e030c5.png)

![Constraint Types](https://i.gyazo.com/097fcf0fb82804389a29cd3b49cb4fc9.png)

## Extrude

Illustrated below is the distribution of different extrude types and operations. Note that tapers can be applied in addition to any extrude type, so the overall frequency of each is shown rather than a relative percentage. 

![Extrude Type Distribution](https://i.gyazo.com/8b4688545edba7dee16e5cb382b38efb.png)

![Extrude Operation Distribution](https://i.gyazo.com/e3b1e28bdddcc27191cf0ebaa45b415f.png)
