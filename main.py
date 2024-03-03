import threading
import time
import queue
import multiprocessing


# used  round-robin scheduling mechanism.
# allows sharing the CPU in a cyclic manner.
class Scheduler(object):
    def __init__(self, threads):
        self.threads = threads
        self.current_thread_index = 0
        self.condition = threading.Condition()

    def get_next_thread(self):
        with self.condition:
            next_thread = self.threads[self.current_thread_index]
            print(f"Thread {next_thread} starting execution.")
            self.current_thread_index = (self.current_thread_index + 1) % len(self.threads)
            print(f"Thread {next_thread} finished execution.")
            self.condition.notify_all()
            next_thread.wait()  # Call wait() on the next thread
            return next_thread

    def __str__(self):
        return f"Scheduler with {len(self.threads)} threads"

    def __repr__(self):
        return f"Scheduler with {len(self.threads)} threads"


class ThreadManager:
    def __init__(self):
        self.threads = []
        self.scheduler = None
        self.lock = threading.Lock()
        self.errors = []  # Store encountered errors
        self.barrier = None
        self.condition = threading.Condition()

    def create_thread(self, target, args=()):
        thread = MyThread(target=target, args=args, lock=self.lock)
        self.threads.append(thread)
        return thread  # Return the created thread

    def handle_errors(self):
        if self.errors:
            print("Encountered errors:")
            for error in self.errors:
                print(error)
            # Perform appropriate error handling or recovery actions based on the errors

    def start_all_threads(self):
        if not self.scheduler:
            self.scheduler = Scheduler(self.threads)
        self.barrier = threading.Barrier(len(self.threads))

        for thread in self.threads:
            thread.acquire_lock()  # Acquire the lock before starting the thread
            thread.barrier = self.barrier  # Assign the barrier object to the thread
            thread.start()
            # # Perform signaling when starting the threads
            # with self.condition:
            #     print(f"Signaling thread {thread}...")
            #     self.condition.notify()

    def signal_threads(self):
        with self.condition:
            self.condition.notify_all()

    def join_all_threads(self):
        for thread in self.threads:
            thread.join()

    def create_new_thread(self, target, args=()):
        thread = MyThread(target=target, args=args, scheduler=self.scheduler, lock=self.lock)
        self.threads.append(thread)
        return thread

    def request_termination_all_threads(self):
        for thread in self.threads:
            thread.terminate()


shared_data = multiprocessing.Value('i', 0)  # Shared memory variable


# thread class to handle thread functions
class MyThread(threading.Thread):
    def __init__(self, *args, scheduler=None, lock=None, barrier=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.exit_flag = False
        self.scheduler = scheduler
        self.lock = lock
        self.condition = threading.Condition(lock)
        self.message_queue = queue.Queue()
        self.barrier = None  # Initialize the barrier as None

    def terminate(self):
        self.exit_flag = True

    def run(self):
        if self.scheduler:
            self.scheduler.get_next_thread()
        # error handling
        try:
            super().run()
        except Exception as e:
            # Handle the exception appropriately
            print(f"Thread {self} encountered an error: {e}")
            # Perform error reporting and recovery actions if needed
        self.release_lock()
        self.notify()

        if self.barrier:
            self.barrier.wait()  # Wait for all threads to reach the barrier

    # Synchronization Primitives
    def wait(self):
        with self.condition:
            print(f"Thread {self} waiting.")
            self.condition.wait()
            print(f"Thread {self} resumed execution.")

    def notify(self):
        with self.condition:
            print(f"Thread {self} notifying.")
            self.condition.notify()

    def acquire_lock(self):
        self.lock.acquire()
        print(f"Thread {self} acquired lock.\n")

    def release_lock(self):
        self.lock.release()
        print(f"Thread {self} released lock.\n")

    def send_message(self, message):
        self.message_queue.put(message)
        print(f"Thread {self} sent message: {message}")

    def receive_message(self):
        message = self.message_queue.get()
        print(f"Thread {self} received message: {message}")
        return message

    # helper functions


def my_function():
    global shared_data
    print("This is my function.")
    with shared_data.get_lock():
        shared_data.value += 1
    print(f"Shared data: {shared_data.value}\n")


def my_function1():
    global shared_data
    print("This is my function 1.")
    with shared_data.get_lock():
        shared_data.value -= 1
    print(f"Shared data: {shared_data.value}\n")


def my_function():
    print("This is my function.\n")


def my_function1():
    print("This is my function 1.\n")


# main menu
def main():
    thread_manager = ThreadManager()

    while True:
        try:

            print("\n=== Thread Management Menu ===")
            print("1. Create a new thread by user")
            print("2. Start all threads")
            print("3. Terminate all threads")
            print("4. Send message to a thread")
            print("5. Exit.\n")

            choice = input("Enter your choice (1-5): ")

            if choice == "1":
                print("Enter the function for the thread:")
                function_code = input()
                try:
                    function = eval(function_code)
                    thread_manager.create_new_thread(function)
                    print("Thread created successfully.")
                except Exception as e:
                    print(f"Error creating thread: {e}")

            elif choice == "2":
                print("Starting Threads...")
                thread_manager.start_all_threads()
                time.sleep(0.1)

            elif choice == "3":
                print("Do you want to terminate all threads? (yes/no)")
                terminate_answer = input()
                if terminate_answer == "yes":
                    print("Terminating.....")
                    thread_manager.request_termination_all_threads()
                    thread_manager.join_all_threads()
                    print("All threads terminated.")
                else:
                    print("No termination.")

            elif choice == "4":
                current_time = datetime.datetime.now().time()
                if current_time.hour >= 9 and current_time.hour < 17:
                    print("The clock is open....")
                    print("Enter the thread index to send the message to:")
                    thread_index = int(input())
                    print("Enter the message to send: (starts with 0)")
                    message = input()

                    if thread_index >= 0 and thread_index < len(thread_manager.threads):
                        thread_manager.threads[thread_index].send_message(message)
                    else:
                        print("Invalid thread index....")
                else:
                    print("The clock is closed .... The thread is waiting for his time ....")
                    time.sleep(1)  # Add a delay to wait for the clock to open

            elif choice == "5":
                                # Check if any thread is still active
                active_threads = [thread for thread in thread_manager.threads if thread.is_alive()]

                if active_threads:
                    terminate_answer = input("There are still active threads. Are you sure you want to terminate all threads and exit? (yes/no): ")
                    if terminate_answer.lower() == "yes":
                        thread_manager.request_termination_all_threads()
                        thread_manager.join_all_threads()
                        print("All threads terminated.\n")
                        break
                    else:
                         print("Termination canceled.\n")
                else:
                    print("No active threads. Exiting...\n")
                    break

               # Send message from one thread to another
                print("Enter the source thread index to send the message from:")
                source_thread_index = int(input())
                print("Enter the destination thread index to send the message to:")
                destination_thread_index = int(input())
                print("Enter the message to send:")
                message = input()

                if source_thread_index >= 0 and source_thread_index < len(thread_manager.threads) and destination_thread_index >= 0 and destination_thread_index < len(thread_manager.threads):
                    source_thread = thread_manager.threads[source_thread_index]
                    destination_thread = thread_manager.threads[destination_thread_index]
                    source_thread.send_message(f"To {destination_thread}: {message}")
                else:
                    print("Invalid thread index.")

            else:
                print("Invalid choice. Please try again.\n")
        except Exception as e:
            print(f"An error occurred: {e}")
            # Perform error reporting and recovery actions if needed
        thread_manager.handle_errors()


if __name__ == "__main__":
    # Your code here
   main()
