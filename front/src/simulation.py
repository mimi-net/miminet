import time

from miminet_model import db, Simulate, Network
from app import app


def run_mininet():
    return


def simulation_check():

    print("Check for a new simulation request")
    with app.app_context():
        sim = Simulate.query.filter(Simulate.ready == 0).first()

        if not sim:
            return

        net = Network.query.filter(Network.id == sim.network_id).first()

        # We got simulation and don't have a corresponding network.
        # Log it and delete simulation
        if not net:
            db.session.delete(sim)
            db.session.commit()
            return

        print(net.network)
        return

def miminet_polling():

    while True:
        simulation_check()
        time.sleep(1)


if __name__ == '__main__':
    miminet_polling()
