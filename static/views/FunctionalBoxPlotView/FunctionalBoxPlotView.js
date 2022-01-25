/* globals d3 */

import ZoomableTimelineView from '../ZoomableTimelineView/ZoomableTimelineView.js';

class FunctionalBoxPlotView extends ZoomableTimelineView { // abstracts a lot of common logic for smooth zooming + panning + rendering offscreen + showing scrollbars for timeline-based views
  constructor (options) {
    options.resources = (options.resources || []).concat(...[
      // Placeholder resources that don't actually get updated until later
      { type: 'placeholder', value: null, name: 'data' }
    ]);
    super(options);

    this.metric = options.glState.variant;

    this.yScale = d3.scaleLinear();
  }

  get isLoading () {
    // Display the spinner + skip most of the draw call if we're still waiting
    // on data
    if (super.isLoading) {
      return true;
    }
    const data = this.getNamedResource('data');
    if (data === null || (data instanceof Error && data.status === 503)) {
      return true;
    }
    return false;
  }

  get error () {
    const err = super.error;
    if (err?.status === 503) {
      // We don't want to count 503 errors (still loading data) as actual errors
      return null;
    } else {
      return err;
    }
  }

  setYDomain(maxMin) {
    var yOffset = (maxMin['max'] - maxMin['min']) / 10;
    this.yScale.domain([maxMin['max'] + yOffset, maxMin['min'] - yOffset]);
  }
  getSpilloverWidth(width) {
    return width*3;
  }

  findBinNumber(t){
    const data = this.linkedState.getCurrentMetricBins(this.curMetric);
    var offset = (data.metadata.end - data.metadata.begin) / data.metadata.bins;
    var bin = (t - data.metadata.begin) / offset;
    var fBin = Math.floor(bin);
    return {max: data.data.max[fBin].toFixed(3),
      avg: data.data.average[fBin].toFixed(3),
      std: data.data.std[fBin].toFixed(3),
      min: data.data.min[fBin].toFixed(3)};
  }

  drawCanvas (chartShape) {
    const fetchedData = this.getNamedResource('data');
    if(fetchedData === null || fetchedData.data === undefined) return;

    const canvas = this.d3el.select('canvas');
    const context = canvas.node().getContext('2d');
    const __self = this;
    var line = d3.line()
        .x(function(d, i) { return i; })
        .y(function(d) { return __self.yScale(d); })
        .context(context);
    this.drawLine(context, line, fetchedData.data.average);
    this.drawLine(context, line, fetchedData.data.min);
    this.drawLine(context, line, fetchedData.data.max);
  }

  drawLine(context, line, data) {
    const theme = globalThis.controller.getNamedResource('theme').cssVariables;
    context.beginPath();
    line(data);
    context.lineWidth = 1.5;
    context.strokeStyle = theme['--text-color-softer'];
    context.stroke();
  }

  async updateData (chartShape) {
    const domain = chartShape.spilloverXScale.domain();
    return this.updateResource({
      name: 'data',
      type: 'json',
      url: `/datasets/${this.datasetId}/metrics/${encodeURIComponent(this.metric)}/summary?bins=${chartShape.bins}&begin=${domain[0]}&end=${domain[1]}`
    });
  }

  /**
   * Calculate the visible chart area, whether scrollbars should be showing,
   * update all scales; after accounting for spillover space, figure out how
   * many bins and which locations should be requested from the API
   * @return {boolean} True if the viewport is inconsistent with the data that
   * is currently loaded (i.e. it has been resized, scrolled, or zoomed since
   * the last updateShapeAndDataIfNeeded call)
   */
  getChartShape () {
    const chartShape = super.getChartShape();

    const fetchedData = this.getNamedResource('data');
    this.yScale.range([0, chartShape.fullHeight])
        .domain([10, 0]);
    if(fetchedData === null || fetchedData.data === undefined) return chartShape;
    var maxY = Number.MIN_VALUE;
    var minY = Number.MAX_VALUE;

    for (var i = 0; i < fetchedData.metadata.bins; i++) {
      maxY = Math.max(maxY, fetchedData.data.max[i]);
      minY = Math.min(minY, fetchedData.data.min[i]);
    }
    this.setYDomain({'max':maxY, 'min':minY});
    chartShape.maxMetricValue = maxY;
    chartShape.minMetricValue = minY;
    return chartShape;
  }

  drawAxes (chartShape) {
    super.drawAxes(chartShape);
    // Update the y axis
    this.d3el.select('.yAxis')
        .call(d3.axisLeft(this.yScale)); //.tickFormat(x => x / zeroCutter));
    // Set the y label
    this.d3el.select('.yAxisLabel')
      .text(this.metric.substring(this.metric.lastIndexOf(':')+1));
  }
}

export default FunctionalBoxPlotView;
