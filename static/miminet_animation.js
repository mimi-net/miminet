var PacketPlayer = (function () {

    var animation_traffic_step = 0;
    var animation_guid = uid();
    var animation_packets = [];
    var traffic = [];
    var network_cy = null;
    var player_pause = 0;
    var player_play = 0;

    var instance;

    const InitPlayer = function(packet){

        setTraffic(packet);
        setAnimationTrafficStep(0);
        clearAnimationPackets();
        setPlayerPause(0);
        setPlayerPlay(0);
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

        // Remove all packets
        let pkts = network_cy.elements().filter('[type = "packet"]');

        pkts.forEach(function(p_item, idx, array){
            network_cy.remove(p_item);
        });

        setAnimationTrafficStep(0);
        clearAnimationPackets();
        setPlayerPause(0);
        setPlayerPlay(0);
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

        let pkts = traffic[animation_traffic_step];

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

            let edge = network_cy.edges('[id = "' + p_item['config']['path'] + '"]');

            if (!edge.source()) {
                return;
            }

            let pkt_id = p_item['data']['id'];
            let from_xy = undefined;
            let to_xy = undefined;
            let last_p_item = 0;

            // Is this is last packet?
            if (idx === array.length - 1){
                last_p_item = 1;
            }

            if (edge.source().id() === p_item['config']['source'])
            {
                from_xy = edge.sourceEndpoint();
                to_xy = edge.targetEndpoint();
            } else if (edge.source().id() === p_item['config']['target'])
            {
                from_xy = edge.targetEndpoint();
                to_xy = edge.sourceEndpoint();
            } else {
                console.log('Got edge but source and target id is not equal');
                return;
            }

            // Start coordinates
            p_item['renderedPosition'] = {x: from_xy['x'] * zoom + px, y: from_xy['y'] * zoom + py};

            // User can't grab nor select
            p_item['grabbable'] = false;
            p_item['selectable'] = false;

            network_cy.add(p_item);
            network_cy.elements().last().addClass("hidden");

            let edge_wait = 0;

            if (edgeMap[p_item.config.path])
            {
                edge_wait = edgeMap[p_item.config.path] * 500;
                edgeMap[p_item.config.path] = edgeMap[p_item.config.path] + 1;
            }

            let a_pkt = network_cy.nodes().last().animation({
                renderedPosition: {x: from_xy['x'] * zoom + px, y: from_xy['y'] * zoom + py}
            }, {
                duration: getAnimationTrafficStep() ? 500 + edge_wait: 0,
                complete: function(){
                    let pkt = network_cy.elements().filter('[id = "' + pkt_id + '"]')[0];

                    if (!pkt)
                    {
                        return;
                    }

                    pkt.removeClass('hidden');

                    let a_pkt = pkt.animation({
                        renderedPosition: {x: to_xy['x'] * zoom + px, y: to_xy['y'] * zoom + py}
                    }, {
                        duration: 1000,
                        complete: function() {
                            network_cy.remove('[id = "' + pkt_id + '"]');
                            if (last_p_item){
                                PlayNextStep();
                            }
                        }
                    });

                    addAnimationPackets(a_pkt);
                    a_pkt.play();
                }
            });

            edgeMap[p_item.config.path] = 1;
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
        return
    }

    const getPlayerPlay = function (){
        return player_play;
    }

    const createInstance = function () {

        return {
            InitPlayer: InitPlayer,
            StopPlayer: StopPlayer,
            StartPlayer : StartPlayer,
            PausePlayer : PausePlayer,
            getPlayerPause : getPlayerPause,
            getPlayerPlay : getPlayerPlay
        }
    }

    return {
        getInstance: function () {
            return instance || (instance = createInstance());
        }
    }
})();