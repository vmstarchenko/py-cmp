"use strict";

function main() {
  let last = parseInt(process.argv[2]);
  let sum = 0;
  for (let i = 0; i < last; ++i) {
    sum += i;
    if (sum > 1000000000) {
      sum = 0;
    }
  }

  console.log(sum);
}

main();
