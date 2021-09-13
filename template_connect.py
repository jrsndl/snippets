import nuke
import nukescripts
import ast


def get_avalon_nodes():
    nodes = []
    for node in nuke.allNodes(recurseGroups=False):
        if "AvalonTab" in node.knobs():
            try:
                # check if data available on the node
                test = node['avalon_data'].value()
                nodes.append(node)
            except NameError as e:
                pass
    return nodes

def get_template_dots():
    nodes = []
    for node in nuke.allNodes(filter = 'Dot'):
        lbl = str(node['label'].value())
        if lbl.startswith('OpenPype = '):
            nodes.append(node)
    return nodes

def get_connected_nodes(node):
    '''
    Returns a two-tuple of lists. Each list is made up of two-tuples in the
    form ``(index, nodeObj)`` where 'index' is an input index and 'nodeObj'
    is a Nuke node.

    The first list contains the inputs to 'node', where each 'index' is the
    input index of 'node' itself.

    The second contains its outputs, where each 'index' is the input index that
    is connected to 'node'.
    '''
    inputNodes = [(i, node.input(i)) for i in range(node.inputs())]
    outputNodes = []
    for depNode in nuke.dependentNodes(nuke.INPUTS | nuke.HIDDEN_INPUTS, node):
        for i in range(depNode.inputs()):
            if depNode.input(i) == node:
                outputNodes.append((i, depNode))
    return (inputNodes, outputNodes)

def swap_nodes(targetNode, newNode):
    '''
    Mostly mimics the Ctrl + Shift + drag-and-drop node functionality in Nuke.

    'targetNode': The node (or node name) to be replaced.
    'newNode': The node (or node name) that will replace it.
    '''
    if isinstance(targetNode, basestring):
        targetNode = nuke.toNode(targetNode)
    if isinstance(newNode, basestring):
        newNode = nuke.toNode(newNode)
    if not (isinstance(targetNode, nuke.Node) and isinstance(newNode, nuke.Node)):
        return

    source_node_width = newNode.screenWidth() / 2
    source_node_height = newNode.screenHeight() / 2
    target_node_width = targetNode.screenWidth() / 2
    target_node_height = targetNode.screenHeight() / 2
    width_offset = target_node_width - source_node_width
    height_offset = target_node_height - source_node_height
    sourcePos = (newNode.xpos(), newNode.ypos())
    targetPos = (targetNode.xpos() + width_offset, targetNode.ypos() + height_offset)
    inputNodes, outputNodes = get_connected_nodes(targetNode)
    nukescripts.clear_selection_recursive()
    targetNode.setSelected(True)
    nuke.extractSelected()
    targetNode.setSelected(False)
    newNode.setXYpos(*targetPos)
    targetNode.setXYpos(*sourcePos)
    for inNode in inputNodes:
        newNode.setInput(*inNode)
    for index, node in outputNodes:
        node.setInput(index, newNode)
    return True
        

def make_dots_from_avalon_nodes():
    '''
    Looks for Avalon nodes, replaces them with Dots

    The Dots have label that
        starts with 'OpenPype = '
        has a dictionary that allows to identify the Avalon loader or creator
        has a dictionary 'knobs' that allows to override node knobs
    '''

    for node in get_avalon_nodes():
        lbl = {}
        if node.Class() == 'Group' and node['avalon:families'].value() == 'write':
            lbl = {'mode': 'Write', 'families': 'write'}
            lbl['family'] = node['avalon:family'].value()
            lbl['subset'] = node['avalon:subset'].value()
            lbl['knobs'] = {'publish': node['publish'].value(), 
                            'render': node['render'].value(),
                            'review': node['review'].value()
                            }

        if node.Class() == 'Read':
            lbl = {'mode': 'Read'}
            lbl['loader'] = node['avalon:loader'].value()
            lbl['name'] = node['avalon:name'].value()
            lbl['knobs'] = {}
        my_label = 'OpenPype = ' + str(lbl)

        new_node = nuke.nodes.Dot(label = my_label, tile_color = '0xff7f00ff')
        swap_nodes(node, new_node)
        nuke.delete(node)

    return True


def template_connect():
    '''
    Swaps Avalon loaders or creators with corresponding Dot nodes, deletes Dot nodes

    The Dots have a label containing dictionary that allows to identify the Avalon loader or creator
    '''

    avalon_nodes = get_avalon_nodes()
    template_nodes = get_template_dots()

    for one_dot in template_nodes:
        lbl_dict = {}
        try:
            lbl_dict = ast.literal_eval(str(one_dot['label'].value())[11:])
        except:
            print('Template Dot {} dict failed to parse.'.format(one_dot['name'].value()))

        if lbl_dict:
            target_node = None

            if lbl_dict['mode'] == 'Write':
                for node in avalon_nodes:
                    try:
                        if node.Class() == 'Group' and node['avalon:families'].value() == 'write':
                            if lbl_dict['family'] == node['avalon:family'].value():
                                if lbl_dict['subset'] == node['avalon:subset'].value():
                                    target_node = node
                                    break
                    except NameError:
                        pass

            if lbl_dict['mode'] == 'Read':
                for node in avalon_nodes:
                    try:
                        if lbl_dict['loader'] == node['avalon:loader'].value():
                            if lbl_dict['name'] == node['avalon:name'].value():
                                target_node = node
                                break
                    except NameError:
                        pass

            if target_node:
                swap_nodes(one_dot, target_node)
                
                for knob_name, knob_value in lbl_dict['knobs'].items():
                    try:
                        node[knob_name].setValue(str(knob_value))
                    except NameError:
                        print('knob not set')
                nuke.delete(one_dot)
                


make_dots_from_avalon_nodes()
#template_connect()
