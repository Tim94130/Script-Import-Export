<?php

$myfile = fopen("/tmp/testfb", "a+");
fwrite($myfile, "it works!\n");
fclose ($myfile);

?>
