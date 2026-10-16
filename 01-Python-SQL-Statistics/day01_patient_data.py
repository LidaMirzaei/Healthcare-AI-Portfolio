"""Day 1: Pandas basics using synthetic sample data (not medical evidence)."""
import pandas as pd


def main():
    patients = {
        'patient_id': [101, 102, 103, 104, 105],
        'age': [45, 62, 51, 70, 39],
        'treatment': ['A', 'B', 'A', 'B', 'A'],
        'response': [1, 0, 1, 0, 1],
    }
    df = pd.DataFrame(patients)
    print(df)
    print('Average age:', df['age'].mean())
    print('Mean response indicator by group:')
    print(df.groupby('treatment')['response'].mean())
    print('Note: This tiny synthetic dataset cannot establish treatment effectiveness.')


if __name__ == '__main__':
    main()
