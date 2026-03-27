const SnapNodesToGrid = function(cy_instance) {
    if (!cy_instance) return;

    let anyMoved = false;
    const baseGridSize = 25;

    cy_instance.nodes().each(function(ele) {
        if (!ele.isNode()) return;

        const pos = ele.position();

        // Calculate snapped position
        const newX = Math.round(pos.x / baseGridSize) * baseGridSize;
        const newY = Math.round(pos.y / baseGridSize) * baseGridSize;

        // If coordinate differs significantly (float error)
        if (Math.abs(newX - pos.x) > 0.5 || Math.abs(newY - pos.y) > 0.5) {

            // Move cy node
            ele.position({x: newX, y: newY});

            // Update global nodes array
            if (typeof nodes !== 'undefined') {
                 let n = nodes.find(n => n.data.id === ele.id());
                 if (n) {
                     n.position.x = newX;
                     n.position.y = newY;
                     anyMoved = true;
                 }
            }
        }
    });

    if (anyMoved) {
        MoveNodes();
    }
}

const initGrid = function(cy) {
    if (!cy) return;

    // Clean up previous listener
    if (typeof gridCanvasLayer !== 'undefined' && gridCanvasLayer && gridCanvasLayer.resizeAndDrawCanvas) {
        window.removeEventListener('resize', gridCanvasLayer.resizeAndDrawCanvas);
    }

    // Remove old grid canvas if exists
    const oldCanvas = document.getElementById('grid-canvas-static');
    if (oldCanvas) {
        oldCanvas.remove();
    }

    // Create canvas with absolute positioning to overlay on top of cytoscape container
    const canvas = document.createElement('canvas');
    canvas.id = 'grid-canvas-static';
    canvas.style.position = 'absolute';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.pointerEvents = 'none';

    const container = cy.container();
    container.insertBefore(canvas, container.firstChild);

    const ctx = canvas.getContext('2d');

    const resizeAndDrawCanvas = function() {
        const pixelRatio = window.devicePixelRatio || 1;

        // Use container dimensions instead of window dimensions to prevent distortion
        // when container is not full screen
        canvas.width = container.clientWidth * pixelRatio;
        canvas.height = container.clientHeight * pixelRatio;

        // Always redraw when resizing
        if (gridCanvasLayer) {
            drawGrid();
        }
    };

    gridCanvasLayer = {
        canvas: canvas,
        ctx: ctx,
        resizeAndDrawCanvas: resizeAndDrawCanvas
    };

    resizeAndDrawCanvas();

    // Add event listener for resize
    window.addEventListener('resize', resizeAndDrawCanvas);

    // Add cy resize listener to handle container resizing specifically
    if (cy) {
        cy.on('resize', resizeAndDrawCanvas);
    }

    // Initialize current zoom from cytoscape
    if (cy && cy.zoom) {
        currentGridZoom = cy.zoom();
    }

    // Draw grid
    drawGrid();
};

const drawGrid = function() {
    if (!gridCanvasLayer) {
        return;
    }

    const canvas = gridCanvasLayer.canvas;
    const ctx = gridCanvasLayer.ctx;

    if (!canvas || !ctx) {
        return;
    }

    // Scale grid with zoom: at max zoom (2.0) = 50px like before, at min zoom (0.5) = small cells
    const gridSize = 25 * currentGridZoom; // 25 * 2.0 = 50px (max zoom), 25 * 0.5 = 12.5px (min zoom)
    const pixelRatio = window.devicePixelRatio || 1;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const screenWidth = canvas.width / pixelRatio;
    const screenHeight = canvas.height / pixelRatio;

    // Get pan offset to align grid with cytoscape coordinate system
    let panX = 0;
    let panY = 0;
    if (global_cy && global_cy.pan) {
        const pan = global_cy.pan();
        panX = pan.x;
        panY = pan.y;
    }

    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

    // Draw grid lines across entire viewport
    ctx.strokeStyle = 'rgba(200, 200, 200, 0.4)';
    ctx.lineWidth = 1;

    ctx.beginPath();

    // Calculate grid origin with pan offset
    // Grid should be offset by pan to stay aligned with nodes
    const gridOriginX = panX % gridSize;
    const gridOriginY = panY % gridSize;

    // Vertical lines across entire viewport
    const startX = Math.floor(-gridOriginX / gridSize) * gridSize + gridOriginX;
    for (let x = startX; x <= screenWidth; x += gridSize) {
        ctx.moveTo(x, 0);
        ctx.lineTo(x, screenHeight);
    }

    // Horizontal lines across entire viewport
    const startY = Math.floor(-gridOriginY / gridSize) * gridSize + gridOriginY;
    for (let y = startY; y <= screenHeight; y += gridSize) {
        ctx.moveTo(0, y);
        ctx.lineTo(screenWidth, y);
    }

    ctx.stroke();
};


// Update grid when config panel opens/closes
const updateGridForConfigPanel = function() {
    if (gridCanvasLayer && gridCanvasLayer.resizeAndDrawCanvas) {
        // Small delay to let DOM update
        setTimeout(function() {
            gridCanvasLayer.resizeAndDrawCanvas();
        }, 50);
    }
}
