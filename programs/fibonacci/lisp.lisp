(defun fib(a)
  (if (< a 2)
      a
    (+ (fib (- a 1)) (fib (- a 2)))))

(defun main()
  (print (fib 30)))

(main)
