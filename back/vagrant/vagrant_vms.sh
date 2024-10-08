for ((i=1; i <= $numberOfBoxes; i++))
do
vagrant up $provider$i &
done
