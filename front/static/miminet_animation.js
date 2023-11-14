
var PacketPlayer = (function () {

    var animation_traffic_step = 0;
    var animation_guid = uid();
    var animation_packets = [];
    var traffic = [];
    var network_cy = null;
    var player_pause = 0;
    var player_play = 0;
    var pkts_on_the_fly = 0;

    var animation_traffic_step_callback = function(){};

    var instance;

    const InitPlayer = function(packet){

        setTraffic(packet);
        setAnimationTrafficStep(0);
        clearAnimationPackets();
        setPlayerPause(0);
        setPlayerPlay(0);
        pkts_on_the_fly = 0;
    }

    const StartPlayer = function(cy){

        if (!traffic){
            console.log("Nothing to animate. Traffic is null");
            return 0;
        }

        // Where to play
        setCy(cy);

      // If we in pause
        if (getPlayerPause()){
            setPlayerPause(0);
            PlayAnimation();
            return;
        }

        // If we already in play mode
        if (getPlayerPlay()){
            return;
        }

        PlayNextStep();
    }

    const StopPlayer = function(){

        // Stop all animations
        animation_packets.forEach(function(p, idx, array){
            p.stop();
        });

        if (!network_cy){
            return;
        }

        // Remove all packets
        let pkts = network_cy.elements().filter('[type = "packet"]');

        pkts.forEach(function(p_item, idx, array){
            network_cy.remove(p_item);
        });

        setAnimationTrafficStep(0);
        clearAnimationPackets();
        setPlayerPause(0);
        setPlayerPlay(0);
        pkts_on_the_fly = 0;
        return;
    }

    const PausePlayer = function(){

        animation_packets.forEach(function(p, idx, array){
            p.pause();
        });

        setPlayerPause(1);
    }

    const PlayNextStep = function(){

        // Clear animated packets.
        clearAnimationPackets();

        // Set player to play
        setPlayerPlay(1);

        let ats = getAnimationTrafficStep();

        if (ats >= traffic.length)
        {
            console.log("Animation is end");
            $('#NetworkStopButton').click();
            return;
        }

        PlayStep();
        increaseAnimationTrafficStep();
        getAnimationTrafficStepCallback().call();
        return;
    }

    const PlayStep = function() {

        let timeout = 0;

        if (!network_cy){
            console.log("No global cy");
            return 0;
        }

        if (!traffic){
            console.log("Nothing to animate. Traffic is null");
            return 0;
        }

        if (!traffic.length){
            console.log("0 packets, nothing to animate");
            return;
        }

        let ats = getAnimationTrafficStep();

        if (ats >= traffic.length)
        {
            console.log("Animation is end");
            $('#NetworkStopButton').click();
            return;
        }

        let pkts = traffic[getAnimationTrafficStep()];

        if (pkts.length == 0)
        {
            console.log('Step ' + ats + ' has 0 packets. Skip it.')
            return 0;
        }

        let edgeMap = {};
        let maxCount = 1;

        PlayerSetPackets(pkts);
        PlayAnimation();
    }

    const PlayAnimation = function(){

        animation_packets.forEach(function(p, idx, array){
            if (!p.completed()){
                p.play();
            }
        });
    }

    const PlayerSetPackets = function (pkts){

        let zoom = network_cy.zoom();
        let px = network_cy.pan().x;
        let py = network_cy.pan().y;
        let edgeMap = {};

        pkts.forEach(function(p_item, idx, array){

            let pp_item = jQuery.extend(true, {}, p_item);
            pp_item['data']['id'] = uid();

            let edge = network_cy.edges('[id = "' + pp_item['config']['path'] + '"]');

            if (!edge.source()) return;

            let pkt_id = pp_item['data']['id'];
            let from_xy = undefined;
            let to_xy = undefined;

            if (edge.source().id() === pp_item['config']['source'])
            {
                from_xy = edge.sourceEndpoint();
                to_xy = edge.targetEndpoint();
            } else if (edge.source().id() === pp_item['config']['target'])
            {
                from_xy = edge.targetEndpoint();
                to_xy = edge.sourceEndpoint();
            } else {
                console.log('Got edge but source and target id is not equal');
                return;
            }

            let curve = edge.rscratch();

            // Start coordinates
            pp_item['renderedPosition'] = {x: from_xy['x'] * zoom + px, y: from_xy['y'] * zoom + py};

            // User can't grab nor select
            pp_item['grabbable'] = false;
            pp_item['selectable'] = false;

            network_cy.add(pp_item);
            pkts_on_the_fly++;
            network_cy.elements().last().addClass("hidden");

            let edge_wait = 0;

            if (edgeMap[p_item.config.path])
            {
                edge_wait = edgeMap[p_item.config.path] * 500;
                edgeMap[p_item.config.path] = edgeMap[p_item.config.path] + 1;
            } else {
                edgeMap[p_item.config.path] = 1;
            }

            let a_pkt = network_cy.nodes().last().animation({
                renderedPosition: {x: from_xy['x'] * zoom + px, y: from_xy['y'] * zoom + py}
            }, {
                duration: getAnimationTrafficStep() ? 500 + edge_wait: 0 + edge_wait,
                complete: function(){
                    let pkt = network_cy.elements().filter('[id = "' + pkt_id + '"]')[0];

                    if (!pkt) return;

                    pkt.removeClass('hidden');

                    let a_pkt = pkt.animation({
                        renderedPosition: {x: to_xy['x'] * zoom + px, y: to_xy['y'] * zoom + py}
                    }, {
                        duration: 1000,
                        complete: function() {
                            network_cy.remove('[id = "' + pkt_id + '"]');
                            pkts_on_the_fly--;

                            // If it's the last packet
                            if (!pkts_on_the_fly){
                                PlayNextStep();
                            }
                        },
                        step: function () {
                            this.easingImpl = (() => {
                                return (start, end, percent) => {
                                    if (curve.ctrlpts) {
                                        let middle = (start == curve.startX || start == curve.endX) ? curve.ctrlpts[0] : curve.ctrlpts[1];
                                        return (1 - percent) * (1 - percent) * start + 2 * (percent) * (1 - percent) * (middle) + percent * percent * end
                                    } else {
                                        return start + (end - start) * percent;
                                    }
                                }
                            })();
                        }
                    });

                    addAnimationPackets(a_pkt);
                    a_pkt.play();
                }
            });

            addAnimationPackets(a_pkt);
        });
    }

    const increaseAnimationTrafficStep = function () {
        animation_traffic_step++;
        return;
    }

    const setAnimationTrafficStep = function (n) {

        if (n >= parseInt(n, 10)){
            animation_traffic_step = n;
        }
        return;
    }

    const getAnimationTrafficStep = function () {
        return animation_traffic_step;
    }

    const setTraffic = function (packets) {
        traffic = packets;
        return;
    }

    const setCy = function (cy) {
        network_cy = cy;
        return;
    }

    const clearAnimationPackets = function () {

        // Stop all animations
        animation_packets.forEach(function(p, idx, array){
            p.stop();
        });

        animation_packets = [];
        return;
    }

    const addAnimationPackets = function (a_pkts) {
        animation_packets.push(a_pkts);
        return;
    }

    const setPlayerPause = function (s){
        player_pause = s;
        return
    }

    const getPlayerPause = function (){
        return player_pause;
    }

    const setPlayerPlay = function (s){
        player_play = s;
        return;
    }

    const getPlayerPlay = function (){
        return player_play;
    }

    const setAnimationTrafficStepCallback = function (s){
        animation_traffic_step_callback = s;
        return;
    }

    const resetAnimationTrafficStepCallback = function (){
        animation_traffic_step_callback = function(){};
        return;
    }

    const getAnimationTrafficStepCallback = function (){
        return animation_traffic_step_callback;
    }

    const createInstance = function () {

        return {
            InitPlayer: InitPlayer,
            StopPlayer: StopPlayer,
            StartPlayer: StartPlayer,
            PausePlayer: PausePlayer,
            getPlayerPause: getPlayerPause,
            getPlayerPlay: getPlayerPlay,
            setAnimationTrafficStepCallback: setAnimationTrafficStepCallback,
            resetAnimationTrafficStepCallback: resetAnimationTrafficStepCallback,
            getAnimationTrafficStep: getAnimationTrafficStep,
            setAnimationTrafficStep: setAnimationTrafficStep
        }
    }

    return {
        getInstance: function () {
            return instance || (instance = createInstance());
        }
    }
})();