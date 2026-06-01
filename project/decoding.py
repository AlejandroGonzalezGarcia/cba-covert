import numpy as np
import scipy.signal as signal
import time
from pylsl import local_clock

def create_reference_sinusoids(n_samples, fs, frequency, n_harmonics, phase=0):
    """
    generate matrix of reference sines and cosines

    parameters
    ----

    """
    t = np.arange(n_samples) / fs
    Y = []
    for h in range(n_harmonics):
        harmonic = h + 1

        # create sine
        sine = np.sin(2 * np.pi * t * frequency * harmonic + phase)
        Y.append(sine)

        # create cosine
        cosine = np.cos(2 * np.pi * t * frequency * harmonic + phase)
        Y.append(cosine)
    Y = np.array(Y).T
    return Y

def max_corr(X,Y):
    """
    Uses CCA to find the maximum correlation between two multivariate
    datasets

    parameters
    ----
    X: (n_samples, variables)
        multivariate dataset 1 (EEG)
    Y: (n_samples, variables)
        multivarate dataset 2 (reference signals - sinusoids)
    """
    # ridge for regularization (look more into this)
    ridge = 1e-2

    # demean
    X = X - X.mean(axis = 0)
    Y = Y - Y.mean(axis = 0)

    # number of samples
    n = X.shape[0]

    # calculate covariance matrices
    Sxx = X.T @ X / (n-1)
    Syy = Y.T @ Y / (n-1)
    Sxy = X.T @ Y / (n-1)
    Syx = Y.T @ X / (n-1)

    # regularize matrices to avoid singularity
    Sxx = Sxx + ridge * np.eye(Sxx.shape[0])
    Syy = Syy + ridge * np.eye(Syy.shape[0])

    # calculate inverses
    Sxx_inv = np.linalg.inv(Sxx)
    Syy_inv = np.linalg.inv(Syy)

    # set up eigenvalue problem (only solve one of them)
    M = Sxx_inv @ Sxy @ Syy_inv @ Syx

    # get eigenvectors and eigenvalues
    eigvals, eigvecs = np.linalg.eig(M)

    # clean artifacts
    eigvals = np.real(eigvals)

    # no negative eigenvalues
    eigvals = np.maximum(eigvals, 0)

    # get size of relevant eigenvalues
    k = min(X.shape[1], Y.shape[1])

    # organize eigenvalues and eigenvectors in descending order
    idx = np.argsort(eigvals)[::-1]

    eigvals = eigvals[idx]
    eigvals = eigvals[:k]

    eigvecs = np.real(eigvecs[:, idx])
    eigvecs = eigvecs[:, :k]

    # get correlation
    rho = np.sqrt(eigvals)
    rho = rho[0] # get maximum correlation

    return rho

def cca(eeg, fs, frequencies, n_harmonics=2):
    n_samples, n_channels = eeg.shape
    
    # create empty array of scores (one for each frequency)
    scores = np.zeros(len(frequencies))
    frequencies = np.asarray(frequencies)

    # for each frequency, create a set of reference signals
    for i, freq in enumerate(frequencies):
        # calculate reference signal
        Y = create_reference_sinusoids(n_samples, fs, freq, n_harmonics)
        # get maximum correlation between EEG and reference
        scores[i] = max_corr(eeg, Y) 
    
    # get indices for sorted scores and sort scores & frequencies
    idx = np.argsort(scores)[::-1]
    scores_sorted = scores[idx]
    freqs_sorted = frequencies[idx]

    # get index of predicted frequencies with corresponds to frequency of interest
    pred_freq = freqs_sorted[0]
    margin = scores_sorted[0] - scores_sorted[1]

    # return pred_freq, scores_sorted, freqs_sorted, margin

    # # ----dummy algorithm
    # decision = np.random.choice(["left", "right"])
    # decision = np.random.choice(frequencies)

    return pred_freq, scores_sorted, freqs_sorted, margin

def decode(buffer, decisions_queue, fs, stop_event, decode_active, frequencies, window_length=1, algo=cca):
    """
    - reads most recent window_length seconds from circular buffer
    - ensures enough data exists
    - run algorithm to decide whether a decision exists
    - push decision to decision queue to be received by stimulus

    parameters
    ----
    buffer: CircularBuffer object
        buffer object defined in main.py
    decisions_queue: queue.Queue object
        queue for decisions
    fs: int
        sampling frequency
    window_length: int
        length in seconds of decoding window
    algo: method
        algorithm to be used (defined in this same script)
    """

    window_samples = window_length * fs # number of samples in decoding window

    last_decision = None
    agree_count = 0
    decision_sent = False
    decode_start = False
    while not stop_event.is_set():
        if buffer.filled < window_samples:
            time.sleep(0.01)
            continue
        
        # if state of decoding is inactive, skip iterations
        if not decode_active.is_set():
            decode_start = False
            # reset state when decoding is inactive
            last_decision = None
            agree_count = 0 # 3 agreed decisions in a row = decision
            decision_sent = False
            start_time = time.perf_counter() # initiate start time
            time.sleep(0.01)
            continue

        # get just EEG channels of data
        data = buffer.get_last(window_samples)
        eeg = data[:, :8]
        # print(eeg.shape)

        decision, scores_sorted, freqs_sorted, margin = algo(eeg, fs, frequencies)
        print(margin, decision)
        # print(f"Decision: {decision}")

        # TODO: TRY TO IMPLEMENT A WAY OF OPTIMIZING MARGIN
        if margin > 0.05: # only if answer is reasonably ahead
            if decision == last_decision:
                agree_count += 1
                # print("Decision agreed with previous decision")
            else:
                last_decision = decision
                agree_count = 1
                # print("Resetting agreement count")
        
            if agree_count >= 5 and not decision_sent:
                decisions_queue.put({
                    "decision": decision
                })
                print(f"Sent decision to queue: {decision} Hz")
                decision_sent = True
        else: # reset decision if we have a weak decision
            last_decision = None
            agree_count = 0
        # record end of decision
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        # print(f"Time since last decode: {elapsed_time}")
        time.sleep(0.1)
        
    return
