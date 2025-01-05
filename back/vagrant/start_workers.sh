for ((i=1; i <= $numberOfBoxes; i++))
do
vagrant ssh $provider$i -c 'sudo bash /vagrant/vagrant/start_worker.sh' &
done
