import pandas as pd
import os
import sys
import hashlib
import pickle
from datetime import datetime, date, time, timedelta

cwd = os.getcwd()
delimiter = "\\" if "\\" in cwd else "/"
repoPath = delimiter.join(cwd.split(delimiter)[:cwd.split(delimiter).index("videoProcessing")]) + delimiter

workingDataPath = repoPath + "workingData/"
recentCapturesPath = repoPath + "recentCaptures/"
videoDataPath = repoPath + "videoData/"

offsetMinTime = pd.Timestamp.min + timedelta(days=2)
offsetMaxTime = pd.Timestamp.max - timedelta(days=2)

def getWorkingDf(location, interval = (offsetMinTime.tz_localize("UTC"), offsetMaxTime.tz_localize("UTC"))):
    fullWorkingDataPath = workingDataPath + location
    workingDataFiles = os.listdir(fullWorkingDataPath)
    if len(workingDataFiles) == 0:
        print('no files found')
        return []

    startTime, endTime = interval
    numFilesAdded = 0
    relevantFiles = []
    for wdf in workingDataFiles:
        fileStartTime = pd.to_datetime(wdf.split("_")[0])
        fileEndTime = pd.to_datetime(wdf.split("_")[1])
        if fileEndTime > startTime and fileStartTime < endTime:
            relevantFiles.append(wdf)
    
    if len(relevantFiles) == 0:
        print('no relevant files found')
        return []
    
    dfSoFar = pd.read_parquet(fullWorkingDataPath + relevantFiles[0])
    for dataFileNameIndex in range(1, len(relevantFiles)):
        dfSoFar = pd.concat([dfSoFar, pd.read_parquet(fullWorkingDataPath + relevantFiles[dataFileNameIndex])]) 
    dfSoFar = dfSoFar[~dfSoFar.index.duplicated(keep="first")].sort_index()


    return dfSoFar.loc[startTime:endTime].copy()


# this writes a file for a subset of a DF
def writeDfFile(Df, fullWorkingDataPath):
    parquetName = Df.iloc[0].name.strftime('%Y-%m-%dT%H%M%S%z') +\
                "_" +\
                Df.iloc[-1].name.strftime('%Y-%m-%dT%H%M%S%z') +\
                ".parquet.gzip"
    print(f"saved to a file named {parquetName}")
    print(f"in {fullWorkingDataPath}")

    Df.to_parquet(fullWorkingDataPath + parquetName,
            compression='gzip') 

#takes in a dataframe you want to save and saves it in multiple files
def saveRows(df, fullWorkingDataPath, rows_per_file):
    if len(df) == 0: return
    startRow = 0
    endRow = len(df)
    rows_remaining = endRow - startRow
    while rows_remaining > 2 * rows_per_file:
        print(f'{rows_remaining} is too many rows writing {startRow} to {(endRow - rows_remaining) + rows_per_file}')
        writeDfFile(df.iloc[startRow: (endRow - rows_remaining) + rows_per_file + 1], fullWorkingDataPath)
        rows_remaining -= rows_per_file
        startRow += rows_per_file
    writeDfFile(df.iloc[startRow:endRow+1], fullWorkingDataPath)


# for a given dataframe approximates the number of rows for a parquet of target file size
def rowsPerFile(Df, targetFileSize, fullWorkingDataPath, fileName = 'test.parquet.gzip'):
    if fileName == 'test.parquet.gzip':
        fileRows = 1_000_000
        if len(Df) < fileRows: fileRows = len(Df)-1
        Df.iloc[:fileRows].to_parquet(fullWorkingDataPath + fileName,
                        compression='gzip')
        file_size = os.path.getsize(fullWorkingDataPath + fileName)
        os.remove(fullWorkingDataPath + fileName)
    else:
        fileRows = len(pd.read_parquet(fullWorkingDataPath + fileName))
        file_size = os.path.getsize(fullWorkingDataPath + fileName)
    
    rows_per_file = int(fileRows//(file_size/targetFileSize))
    return rows_per_file

# uses the filenames to split the rows in the df and saves
# will check if no new rows were added to a file by comparing hashes
# and skip save  

def writeToExistingFiles(Df, fileNames, fullWorkingDataPath, rows_per_file):
    addFile = False
    tzi = Df.index[0].tzinfo
    for fileNum, fileName in enumerate(fileNames):
        if fileNum == 0:
            startTime = offsetMinTime.tz_localize(tzi)
        else:
            startTime = pd.to_datetime(fileName.split('_')[0]).tz_convert(tzi)
        
        if fileNum == len(fileNames) - 1:
            endTime = offsetMaxTime.tz_localize(tzi)
        else:
            endTime = pd.to_datetime(fileNames[fileNum + 1].split('_')[0]).tz_convert(tzi)
        
        if Df.index[0] >= startTime and Df.index[0] <= endTime:
            # the interval has begun
            addFile = True

        if Df.index[-1] < startTime:
            # the interval ended on the previous sesction
            addFile = False

        
        if addFile:
            # read in the file 
            existingRows = pd.read_parquet(fullWorkingDataPath + fileName) 
            # remove old file
            os.remove(fullWorkingDataPath + fileName)
            # concatenate the overlappping section
            rowsToSave = pd.concat([existingRows, Df.loc[startTime:endTime]])
            # deduplicate and sort
            rowsToSave = rowsToSave[~rowsToSave.index.duplicated(keep="first")].sort_index()
            # send those rows to be saved
            saveRows(rowsToSave, fullWorkingDataPath, rows_per_file)



# saves a df using existing filenames if available
def writeWorkingDf(location, Df, targetFileSize = 2 * 1024 * 1024):
    fullWorkingDataPath = workingDataPath + location
    if not os.path.exists(fullWorkingDataPath):
        os.makedirs(fullWorkingDataPath)
    fileNames = sorted(os.listdir(fullWorkingDataPath))

    if len(fileNames) == 0:
        rows_per_file = rowsPerFile(Df, targetFileSize, fullWorkingDataPath)
        saveRows(Df, fullWorkingDataPath, rows_per_file)

    else:
        rows_per_file = rowsPerFile(Df, targetFileSize, fullWorkingDataPath, fileNames[0])
        writeToExistingFiles(Df, fileNames, fullWorkingDataPath, rows_per_file)
