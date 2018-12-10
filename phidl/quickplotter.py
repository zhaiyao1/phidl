# TODO: Allow toggling of layers with 1-9 keypresses
# TODO: alias font should be slightly transparent

# TODO: mouse_position label has text cutoff for some reason
# TODO: gridsize_label needs to stay in bottom left corner when window resized


from __future__ import division, print_function, absolute_import
import numpy as np
import sys
import warnings

import phidl
from phidl.device_layout import Device, DeviceReference, Port, Layer, Polygon
import gdspy


try:
    from matplotlib import pyplot as plt
except:
    warnings.warn("""PHIDL tried to import matplotlib but it failed. PHIDL 
                     will still work but quickplot() may not.  Try using
                     quickplot2() instead (see note in tutorial) """)

try:
    from PyQt5 import QtCore, QtGui
    from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QApplication, QGraphicsItem, QRubberBand, QMainWindow, QLabel
    from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF, QRect, QSize,  QCoreApplication, QLineF
    from PyQt5.QtGui import QColor, QPolygonF, QPen

    PORT_COLOR = QColor(190,0,0)
    SUBPORT_COLOR = QColor(0,135,135)
    OUTLINE_PEN = QColor(200,200,200)
except:
    QMainWindow = object
    QGraphicsView = object
    warnings.warn("""PHIDL tried to import PyQt5 but it failed. PHIDL will
                     still work but quickplot2() may not.  Try using
                     quickplot() instead (based on matplotlib) """)


def quickplot(items, show_ports = True, show_subports = True,
              label_ports = True, label_aliases = False, new_window = False):
    """ Takes a list of devices/references/polygons or single one of those, and
    plots them.  Also has the option to overlay their ports """
    if new_window: fig, ax = plt.subplots(1)
    else:
        ax = plt.gca()  # Get current figure
        ax.cla()        # Clears the axes of all previous polygons
    ax.axis('equal')
    ax.grid(True, which='both', alpha = 0.4)
    ax.axhline(y=0, color='k', alpha = 0.2, linewidth = 1)
    ax.axvline(x=0, color='k', alpha = 0.2, linewidth = 1)
    
    # Iterate through each each Device/DeviceReference/Polygon
    np.random.seed(0)
    if type(items) is not list:  items = [items]
    for item in items:
        if isinstance(item, (Device, DeviceReference, gdspy.CellArray)):
            polygons_spec = item.get_polygons(by_spec=True, depth=None)
            for key in sorted(polygons_spec):
                polygons = polygons_spec[key]
                layerprop = _get_layerprop(layer = key[0], datatype = key[1])
                _draw_polygons(polygons, ax, facecolor = layerprop['color'],
                               edgecolor = 'k', alpha = layerprop['alpha'])
                for name, port in item.ports.items():
                    if (port.width is None) or (port.width == 0):
                        _draw_port_as_point(port)
                    else:
                        _draw_port(port, arrow_scale = 2, shape = 'full', color = 'k')
                    ax.text(port.midpoint[0], port.midpoint[1], name)
            if isinstance(item, Device) and show_subports is True:
                for sd in item.references:
                    for name, port in sd.ports.items():
                        _draw_port(port, arrow_scale = 1, shape = 'right', color = 'r')
                        ax.text(port.midpoint[0], port.midpoint[1], name)
            if isinstance(item, Device) and label_aliases is True:
                for name, ref in item.aliases.items():
                    ax.text(ref.x, ref.y, str(name), style = 'italic', color = 'blue',
                             weight = 'bold', size = 'large', ha = 'center')
        elif isinstance(item, Polygon):
            polygons = item.polygons
            layerprop = _get_layerprop(item.layers[0], item.datatypes[0])
            _draw_polygons(polygons, ax, facecolor = layerprop['color'],
                           edgecolor = 'k', alpha = layerprop['alpha'])
    plt.draw()
    plt.show(block = False)
    


def _get_layerprop(layer, datatype):
    # Colors generated from here: http://phrogz.net/css/distinct-colors.html
    layer_colors = ['#3dcc5c', '#2b0fff', '#cc3d3d', '#e5dd45', '#7b3dcc',
    '#cc860c', '#73ff0f', '#2dccb4', '#ff0fa3', '#0ec2e6', '#3d87cc', '#e5520e']
                     
    l = Layer.layer_dict.get((layer, datatype))
    if l is not None:
        color = l.color
        alpha = l.alpha
        if color is None:
            color = layer_colors[np.mod(layer, len(layer_colors))]
    else:
        color = layer_colors[np.mod(layer, len(layer_colors))]
        alpha = 0.6
    return {'color':color, 'alpha':alpha}
    
    
def _draw_polygons(polygons, ax, **kwargs):
    """ This function uses a trick where all polygon points are concatenated, 
    separated only by NaN values.  This speeds up drawing considerably, see
    http://exnumerus.blogspot.com/2011/02/how-to-quickly-plot-polygons-in.html
    """
    nan_pt = np.array([[np.nan, np.nan]])
    polygons_with_nans = [np.concatenate((p, [p[0]], nan_pt), axis = 0) for p in polygons]
    all_polygons = np.vstack(polygons_with_nans)
    plt.fill(all_polygons[:,0], all_polygons[:,1], **kwargs)


def _draw_port(port, arrow_scale = 1, **kwargs):
    x = port.midpoint[0]
    y = port.midpoint[1]
    nv = port.normal
    n = (nv[1]-nv[0])*arrow_scale
    dx, dy = n[0], n[1]
    xbound, ybound = np.column_stack(port.endpoints)
    #plt.plot(x, y, 'rp', markersize = 12) # Draw port midpoint
    plt.plot(xbound, ybound, 'r', alpha = 0.5, linewidth = 3) # Draw port edge
    plt.arrow(x, y, dx, dy,length_includes_head=True, width = 0.1*arrow_scale,
              head_width=0.3*arrow_scale, alpha = 0.5, **kwargs)


def _draw_port_as_point(port, **kwargs):
    x = port.midpoint[0]
    y = port.midpoint[1]
    plt.plot(x, y, 'r+', alpha = 0.5, markersize = 15, markeredgewidth = 2) # Draw port edge



class ViewerWindow(QMainWindow):
    def __init__(self):
        super(ViewerWindow,self).__init__()

        # Create "grid size = 40.0" label
        self.gridsize_label = QLabel('ABCDEF', self)
        self.gridsize_label.setFont(QtGui.QFont('SansSerif', 10))
        self.gridsize_label.move(0, 200)
        self.gridsize_label.setAlignment(Qt.AlignCenter)
        self.gridsize_label.setStyleSheet('color: gray')
        self.gridsize_label.setFixedWidth(100)

        # Create "X=40.001, Y = 70.183" label
        self.position_label = QLabel('ABCDEF', self)
        self.position_label.setFont(QtGui.QFont('SansSerif', 10))
        self.position_label.move(50, 200)
        self.position_label.setAlignment(Qt.AlignCenter)
        self.position_label.setStyleSheet('color: gray')
        self.position_label.setFixedWidth(200)

        # Create label useful for debugging
        self.debug_label = QLabel('DEBUG', self)
        self.debug_label.setFont(QtGui.QFont('SansSerif', 10))
        self.debug_label.move(200, 200)
        self.debug_label.setAlignment(Qt.AlignCenter)
        self.debug_label.setStyleSheet('color: gray')


        # Create QGraphicsView
        self.viewer = Viewer(gridsize_label = self.gridsize_label,
                             position_label = self.position_label)
        self.setCentralWidget(self.viewer)

        # Reorder widgets
        self.gridsize_label.raise_()
        self.position_label.raise_()
        self.debug_label.raise_()
        self.show()
    

class Viewer(QGraphicsView):
    def __init__(self, gridsize_label, position_label):
        QGraphicsView.__init__(self)
        
        self.setGeometry(QRect(100, 100, 800, 600))
        self.setWindowTitle("PIHDL Graphics Window");

        self.gridsize_label = gridsize_label
        self.position_label = position_label
        
        # Create a QGraphicsScene which this view looks at
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF())
        self.setScene(self.scene)
        
        # Customize QGraphicsView
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setInteractive(False)
        self.scale(1,-1) # Flips around the Y axis
         # Use OpenGL http://ralsina.me/stories/BBS53.html
#        self.setViewport(QtOpenGL.QGLWidget())
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.pen = QPen(QtCore.Qt.black, 0)
        self.portpen = QPen(PORT_COLOR, 3)
        self.portpen.setCosmetic(True) # Makes constant width
        self.portfont = QtGui.QFont('Arial', pointSize = 14)
        self.portfontcolor = PORT_COLOR
        self.subportpen = QPen(SUBPORT_COLOR, 3)
        self.subportpen.setCosmetic(True) # Makes constant width
        self.subportfont = QtGui.QFont('Arial', pointSize = 14)
        self.subportfontcolor = SUBPORT_COLOR
        
        # Tracking ports

        # Various status variables
        self._mousePressed = None
        self._rb_origin = QPoint()
        self.zoom_factor_total = 1
        
        # Grid variables
        self.gridpen = QPen(QtCore.Qt.black, 0)
        self.gridpen.setStyle(QtCore.Qt.DotLine)
        self.gridpen.setDashPattern([1,4])
        self.gridpen.setColor(QtGui.QColor(0, 0, 0, 125))
#        self.gridpen = QPen(QtCore.Qt.black, 1)
#        self.gridpen.setCosmetic(True) # Makes constant width
        # self.gridlinesx = []
        # self.gridlinesy = []
        self.scene_polys = []
        
        self.initialize()
            
    
    def add_polygons(self, polygons, color = '#A8F22A', alpha = 1):
        self.scene_polys = []
        qcolor = QColor()
        qcolor.setNamedColor(color)
        qcolor.setAlphaF(alpha)
        for points in polygons:
            qpoly = QPolygonF( [QPointF(p[0], p[1]) for p in points] )
            scene_poly = self.scene.addPolygon(qpoly)
            scene_poly.setBrush(qcolor)
            scene_poly.setPen(self.pen)
            self.scene_polys.append(scene_poly)
            # Update custom bounding box
            sr = scene_poly.sceneBoundingRect()
            if len(self.scene_polys) == 1:
                self.scene_xmin = sr.left()
                self.scene_xmax = sr.right()
                self.scene_ymin = sr.bottom()
                self.scene_ymax = sr.top()
            else:
                self.scene_xmin = min(self.scene_xmin, sr.left())
                self.scene_xmax = max(self.scene_xmax, sr.right())
                self.scene_ymin = min(self.scene_ymin, sr.bottom())
                self.scene_ymax = max(self.scene_ymax, sr.top())

        
    def reset_view(self):
        # The SceneRect controls how far you can pan, make it larger than
        # just the bounding box so middle-click panning works
        panning_rect = QRectF(self.scene_bounding_rect)
        panning_rect_center = panning_rect.center()
        panning_rect.setSize(panning_rect.size()*5)
        panning_rect.moveCenter(panning_rect_center)
        # view_rect = QRectF(self.scene_bounding_rect)
        # view_rect_center = view_rect.center()
        # view_rect.setSize(view_rect.size()*1.5)
        # view_rect.moveCenter(view_rect_center)
        self.setSceneRect(panning_rect)
        self.fitInView(self.scene_bounding_rect, Qt.KeepAspectRatio)
        self.zoom_view(0.5)

        self.update_grid()
        
    def add_port(self, port, is_subport = False):
        if (port.width is None) or (port.width == 0):
            x,y = port.midpoint
            cs = 1 # cross size
            pn = QPointF(x, y+cs)
            ps = QPointF(x, y-cs)
            pe = QPointF(x+cs, y)
            pw = QPointF(x-cs, y)
            qline1 = self.scene.addLine(QLineF(pn, ps))
            qline2 = self.scene.addLine(QLineF(pw, pe))
            port_shapes = [qline1,qline2]
        else:
            point1, point2 = port.endpoints
            point1 = QPointF(point1[0], point1[1])
            point2 = QPointF(point2[0], point2[1])
            qline = self.scene.addLine(QLineF(point1, point2))
            arrow_points = np.array([[0,0],[10,0],[6,4],[6,2],[0,2]])/(40)*port.width
            arrow_qpoly = QPolygonF( [QPointF(p[0], p[1]) for p in arrow_points] )
            port_scene_poly = self.scene.addPolygon(arrow_qpoly)
            port_scene_poly.setRotation(port.orientation)
            port_scene_poly.moveBy(port.midpoint[0], port.midpoint[1])
            port_shapes = [qline,port_scene_poly]
        qtext = self.scene.addText(str(port.name), self.portfont)
        port_items = port_shapes + [qtext]
        rad = port.orientation*np.pi/180
        x,y = port.endpoints[0]*1/4 +  port.endpoints[1]*3/4 + np.array([np.cos(rad), np.sin(rad)])*port.width/8
#        x,y = port.midpoint[0], port.midpoint[1]
#        x,y  = x - qtext.boundingRect().width()/2, y - qtext.boundingRect().height()/2
        qtext.setPos(QPointF(x,y))
        qtext.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        
        if not is_subport:
            [shape.setPen(self.portpen) for shape in port_shapes]
            qtext.setDefaultTextColor(self.portfontcolor)
            self.portitems += port_items
        else:
            [shape.setPen(self.subportpen) for shape in port_shapes]
            qtext.setDefaultTextColor(self.subportfontcolor)
            self.subportitems += port_items
#        self.portlabels.append(qtext)
        
    def add_aliases(self, aliases):
        for name, ref in aliases.items():
            qtext = self.scene.addText(str(name), self.portfont)
            x,y = ref.center
            qtext.setPos(QPointF(x,y))
            qtext.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            self.aliasitems += [qtext]
            
#        x,y = port.midpoint[0], port.midpoint[1]
#        x,y  = x - qtext.boundingRect().width()/2, y - qtext.boundingRect().height()/2

    def set_port_visibility(self, visible = True):
        for item in self.portitems:
            item.setVisible(visible)
        self.ports_visible = visible

             
    def set_subport_visibility(self, visible = True):
        for item in self.subportitems:
            item.setVisible(visible)
        self.subports_visible = visible
                
    def set_alias_visibility(self, visible = True):
        for item in self.aliasitems:
            item.setVisible(visible)
        self.aliases_visible = visible
                
                
            
    def initialize(self):
        self.scene.clear()
        self.polygons = {}
        self.portitems = []
        self.subportitems = []
        self.aliasitems = []
        self.aliases_visible = True
        self.ports_visible = True
        self.subports_visible = True
        self.mouse_position = [0,0]
        self.grid_size_snapped = 0
        self.setMouseTracking(True)
        self.scene_bounding_rect = None
        # self.scene.setSceneRect(QRectF())
        
        

    def finalize(self):
        self.scene_bounding_rect = QRectF(QPointF(self.scene_xmin,self.scene_ymax),
                                          QPointF(self.scene_xmax,self.scene_ymin))
        self.scene_center = [self.scene_bounding_rect.center().x(), self.scene_bounding_rect.center().y()]
        self.scene_size = [self.scene_bounding_rect.width(), self.scene_bounding_rect.height()]

        # self.setGeometry(QRect(100, 100, 800, 600))
        self.create_grid()        
        self.update_grid()

#==============================================================================
#   Grid creation
#==============================================================================
    def update_grid(self):
        grid_pixels = 50
        grid_snaps = [1,2,4]
        
         # Number of pixels in the viewer 
        view_width, view_height = self.rect().width(), self.rect().height()
         # Rectangle of viewport in terms of scene coordinates
        r = self.mapToScene(self.rect()).boundingRect()
        width, height = r.width(), r.height()
        xmin, ymin, xmax, ymax = r.x(), r.y(), r.x() + width, r.y() + height
                                    
        grid_size = grid_pixels*(width / view_width)
        exponent = np.floor( np.log10(grid_size) )
        digits  = round(grid_size / 10**(exponent), 2)
        digits_snapped = min(grid_snaps, key=lambda x:abs(x-digits))
        grid_size_snapped = digits_snapped * 10**(exponent)
        
        # Starting coordinates for gridlines
        x = round((xmin - 2*width )/grid_size_snapped) * grid_size_snapped
        y = round((ymin - 2*height)/grid_size_snapped) * grid_size_snapped

        for gl in self.gridlinesx:
            gl.setLine(x, -1e10, x, 1e10)
            x += grid_size_snapped
        for gl in self.gridlinesy:
            gl.setLine(-1e10, y, 1e10, y)
            y += grid_size_snapped
        self.grid_size_snapped = grid_size_snapped
        self.update_gridsize_label()


    def update_gridsize_label(self):
        self.gridsize_label.setText('grid size = ' + str(self.grid_size_snapped))
        self.gridsize_label.move(QPoint(0, self.height()-30))

    def update_mouse_position_label(self):
        self.position_label.setText('X = %0.3f Y = %0.3f' % (self.mouse_position[0],self.mouse_position[1]))
        self.position_label.move(QPoint(200, self.height()-30))
            
    def create_grid(self):
        self.gridlinesx = [self.scene.addLine(-10,-10,10,10, self.gridpen) for n in range(200)]
        self.gridlinesy = [self.scene.addLine(-10,-10,10,10, self.gridpen) for n in range(200)]

        # self.gridsize_text = self.scene.addText('hello!!!', QtGui.QFont('Arial', pointSize = 10))
        # window = self.parent_window

        self.update_grid()
        
#==============================================================================
#  Mousewheel zoom, taken from http://stackoverflow.com/a/29026916
#==============================================================================
    def wheelEvent(self, event):
        # Zoom Factor
        zoom_percentage = 1.4
    
        # Set Anchors
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)
    
        # Save the scene pos
        oldPos = self.mapToScene(event.pos())
    
        # Zoom
        mousewheel_rotation = event.angleDelta().y() # Typically = 120 on most mousewheels
        zoom_factor = zoom_percentage**(mousewheel_rotation/120)
        zoom_factor = np.clip(zoom_factor, 0.5, 2.0)

        
        # Check to make sure we're not overzoomed
        min_width = 0.01
        min_height = 0.01

        window_width = self.rect().width()
        window_height = self.rect().height()
        scene_upper_left_corner = self.mapToScene(QPoint(0,0))
        scene_bottom_right_corner = self.mapToScene(QPoint(window_width,window_height))
        scene_width = (scene_bottom_right_corner - scene_upper_left_corner).x()
        scene_height = (scene_upper_left_corner - scene_bottom_right_corner).y()

        max_width = self.scene_size[0]*3
        max_height = self.scene_size[1]*3

        if ((scene_width > max_width) or (scene_height > max_height)) and (zoom_factor < 1):
            pass
        elif ((scene_width < min_width) or (scene_height < min_height)) and (zoom_factor > 1):
            pass
        else:
            post_zoom_width = scene_width/zoom_factor
            zoom_factor = scene_width/np.clip(post_zoom_width, min_width, max_width)
            self.zoom_view(zoom_factor)
    
        # Get the new position and move scene to old position
        newPos = self.mapToScene(event.pos())
        delta = newPos - oldPos
        self.translate(delta.x(), delta.y())
        
        
        self.update_grid()
        
        
    def zoom_view(self, zoom_factor):
        old_center = self.mapToScene(self.rect().center())
        self.scale(zoom_factor, zoom_factor)
        self.centerOn(old_center)
        self.zoom_factor_total *= zoom_factor
        
    def resizeEvent(self, event):
        super(QGraphicsView, self).resizeEvent(event)
        if self.scene_bounding_rect is not None:
            self.reset_view()
        self.update_gridsize_label()
        self.update_mouse_position_label()


        
    def mousePressEvent(self, event):
        super(QGraphicsView, self).mousePressEvent(event)
        #==============================================================================
        #  Zoom to rectangle, from
        #  https://wiki.python.org/moin/PyQt/Selecting%20a%20region%20of%20a%20widget
        #==============================================================================
        if event.button() == Qt.RightButton:
            self._mousePressed = Qt.RightButton
            self._rb_origin = QPoint(event.pos())
            self.rubberBand.setGeometry(QRect(self._rb_origin, QSize()))
            self.rubberBand.show()
         #==============================================================================
        # Mouse panning, taken from
        # http://stackoverflow.com/a/15043279
        #==============================================================================
        elif event.button() == Qt.MidButton:
            self._mousePressed = Qt.MidButton
            self._mousePressedPos = event.pos()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            self._dragPos = event.pos()


    def mouseMoveEvent(self, event):
        super(QGraphicsView, self).mouseMoveEvent(event)

        # # Useful debug
        # try:
        #     self.debug_label.setText(str(itemsBoundingRect_nogrid().width()))
        # except:
        #     print('Debug statement failed')

        # Update the X,Y label indicating where the mouse is on the geometry
        mouse_position = self.mapToScene(event.pos())
        self.mouse_position = [mouse_position.x(), mouse_position.y()]
        self.update_mouse_position_label()

        if not self._rb_origin.isNull() and self._mousePressed == Qt.RightButton:
            self.rubberBand.setGeometry(QRect(self._rb_origin, event.pos()).normalized())
                
        # Middle-click-to-pan
        if self._mousePressed == Qt.MidButton:
            newPos = event.pos()
            diff = newPos - self._dragPos
            self._dragPos = newPos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
#            event.accept()

            

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rubberBand.hide()
            rb_rect = QRect(self._rb_origin, event.pos())
            rb_center = rb_rect.center()
            rb_size = rb_rect.size()
            
            if abs(rb_size.width()) > 3 and abs(rb_size.height()) > 3:
                viewport_size = self.viewport().geometry().size()
                
                zoom_factor_x = abs(viewport_size.width() / rb_size.width())
                zoom_factor_y = abs(viewport_size.height() / rb_size.height())
                
                new_center = self.mapToScene(rb_center)
                
                zoom_factor = min(zoom_factor_x, zoom_factor_y)
                self.zoom_view(zoom_factor)
                self.centerOn(new_center)
                
            self.update_grid()
    
        if event.button() == Qt.MidButton:
            self.setCursor(Qt.ArrowCursor)
            self._mousePressed = None
            self.update_grid()
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reset_view()
                
        if event.key() == Qt.Key_F1:
            self.set_alias_visibility(not self.aliases_visible)
                
        if event.key() == Qt.Key_F2:
            self.set_port_visibility(not self.ports_visible)
                
        if event.key() == Qt.Key_F3:
            self.set_subport_visibility(not self.subports_visible)


def quickplot2(item_list, *args, **kwargs):
    global app
    if QCoreApplication.instance() is None:
        app = QApplication(sys.argv)
    if 'viewer_window' not in globals():
        global viewer_window
        viewer_window = ViewerWindow()
    viewer = viewer_window.viewer
    viewer.initialize()
    if type(item_list) not in (list, tuple):
        item_list = [item_list]
    for element in item_list:
        if isinstance(element, (phidl.device_layout.Device, phidl.device_layout.DeviceReference, gdspy.CellArray)):
            # Draw polygons in the element
            polygons_spec = element.get_polygons(by_spec=True, depth=None)
            for key in sorted(polygons_spec):
                polygons = polygons_spec[key]
                layerprop = _get_layerprop(layer = key[0], datatype = key[1])
                viewer.add_polygons(polygons, color = layerprop['color'], alpha = layerprop['alpha'])
            # If element is a Device, draw ports and aliases
            if isinstance(element, phidl.device_layout.Device):
                for ref in element.references:
                    for name, port in ref.ports.items():
                        viewer.add_port(port, is_subport = True)
                for name, port in element.ports.items():
                    viewer.add_port(port)
                    viewer.add_aliases(element.aliases)
            # If element is a DeviceReference, draw ports as subports
            if isinstance(element, phidl.device_layout.DeviceReference):
                for name, port in element.ports.items():
                    viewer.add_port(port, is_subport = True)
        elif isinstance(element, (phidl.device_layout.Polygon)):
                layerprop = _get_layerprop(layer = element.layers[0], datatype = element.datatypes[0])
                viewer.add_polygons(element.polygons, color = layerprop['color'], alpha = layerprop['alpha'])
    viewer.finalize()
    viewer.reset_view()
    viewer_window.setVisible(True)
    viewer_window.show()
    viewer_window.raise_()
    return viewer


